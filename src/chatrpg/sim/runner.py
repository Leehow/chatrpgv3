from __future__ import annotations

from typing import Any

from chatrpg.core.ids import new_id
from chatrpg.db.repositories import PostgresEventStore
from chatrpg.ir.events import DomainEvent
from chatrpg.play import PlayEngine
from chatrpg.runtime.characters import CharacterEngine
from chatrpg.runtime.dice import DiceEngine
from chatrpg.runtime.state import StateReducer
from chatrpg.sim.models import (
    CompletionAssessment,
    PlayerPersona,
    SimConfig,
    SimPlayerObservation,
    SimRunSummary,
    SimTranscriptItem,
    SimTurnRecord,
    SimulatedPlayerAction,
)
from chatrpg.sim.player import SimulatedPlayerAgent
from chatrpg.sim.recorder import SimulationRecorder
from chatrpg.sim.report import SimulationReportBuilder
from chatrpg.systems.coc7e.characters import CocInvestigatorFactory


class SimulationRunner:
    def __init__(
        self,
        *,
        player: SimulatedPlayerAgent,
        gm: PlayEngine,
        recorder: SimulationRecorder,
        event_store: PostgresEventStore,
        reporter: SimulationReportBuilder | None = None,
    ) -> None:
        self._player = player
        self._gm = gm
        self._recorder = recorder
        self._event_store = event_store
        self._reporter = reporter or SimulationReportBuilder()
        self._reducer = StateReducer()
        self._characters = CharacterEngine()

    async def run(self, *, config: SimConfig, persona: PlayerPersona) -> SimRunSummary:
        trace_id = new_id("trc")
        run_id = await self._recorder.start_run(config=config, persona=persona, trace_id=trace_id)
        transcript: list[SimTranscriptItem] = []
        records: list[SimTurnRecord] = []
        final_assessment: CompletionAssessment | None = None
        setup_record = await self._ensure_starting_character(
            config=config,
            run_id=run_id,
            trace_id=trace_id,
            transcript=transcript,
        )
        if setup_record is not None:
            records.append(setup_record)
        for turn_index in range(1, config.max_turns + 1):
            observation = SimPlayerObservation(
                session_id=config.session_id,
                turn_index=turn_index,
                persona=persona,
                transcript=transcript,
                last_gm_response=None if not transcript else transcript[-1].gm_response,
                known_objectives=persona.goals,
                player_visible_state=await self._player_visible_state(session_id=config.session_id),
            )
            action = await self._player.choose_action(observation, trace_id=trace_id)
            if action.wants_to_stop:
                final_assessment = CompletionAssessment(
                    status="completed",
                    confidence=action.confidence,
                    public_rationale=action.stop_reason or action.public_rationale or action.private_reasoning,
                    unresolved_goals=[],
                )
                break
            gm_result = await self._gm.turn(
                session_id=config.session_id,
                message=action.action,
                actor_id=config.actor_id,
            )
            event_types = [event.event_type for event in gm_result.committed_events]
            transcript.append(
                SimTranscriptItem(
                    turn_index=turn_index,
                    player_action=action.action,
                    gm_response=gm_result.narration.text,
                    committed_event_types=event_types,
                )
            )
            next_observation = SimPlayerObservation(
                session_id=config.session_id,
                turn_index=turn_index,
                persona=persona,
                transcript=transcript,
                last_gm_response=gm_result.narration.text,
                known_objectives=persona.goals,
                player_visible_state=await self._player_visible_state(session_id=config.session_id),
            )
            assessment = await self._player.assess_completion(
                observation=next_observation,
                last_action=action,
                turn_limit_reached=turn_index == config.max_turns,
                trace_id=trace_id,
            )
            if turn_index < config.min_turns_before_completion and assessment.status == "completed":
                assessment = CompletionAssessment(
                    status="continue",
                    confidence=assessment.confidence,
                    public_rationale="尚未达到配置的最小模拟回合数。",
                    unresolved_goals=assessment.unresolved_goals,
                )
            row_id = await self._recorder.record_turn(
                run_id=run_id,
                turn_index=turn_index,
                player_action=action,
                gm_result={
                    "trace_id": gm_result.trace_id,
                    "intent": gm_result.intent.model_dump(mode="json"),
                    "narration": gm_result.narration.text,
                    "clue_decision": gm_result.clue_decision,
                    "procedure_result": gm_result.procedure_result,
                },
                committed_events=[event.model_dump(mode="json") for event in gm_result.committed_events],
                completion=assessment,
                trace_id=gm_result.trace_id,
            )
            record = SimTurnRecord(
                id=row_id,
                run_id=run_id,
                turn_index=turn_index,
                player_action=action,
                gm_response=gm_result.narration.text,
                committed_event_types=event_types,
                trace_id=gm_result.trace_id,
                completion=assessment,
            )
            records.append(record)
            final_assessment = assessment
            if assessment.status != "continue":
                break
        status = "completed" if final_assessment and final_assessment.status == "completed" else "stopped"
        loaded_run = await self._recorder.load_run(run_id=run_id)
        loaded_turns = await self._recorder.load_turns(run_id=run_id)
        report_run = dict(loaded_run or {})
        report_run["status"] = status
        report_markdown = self._reporter.build_markdown(run=report_run, turns=loaded_turns)
        report_json = self._reporter.build_json(run=report_run, turns=loaded_turns, markdown=report_markdown)
        await self._recorder.finish_run(run_id=run_id, status=status, report=report_json)
        return SimRunSummary(
            run_id=run_id,
            session_id=config.session_id,
            actor_id=config.actor_id,
            status=status,
            turns=records,
            final_assessment=final_assessment,
            report_markdown=report_markdown,
        )

    async def _ensure_starting_character(
        self,
        *,
        config: SimConfig,
        run_id: str,
        trace_id: str,
        transcript: list[SimTranscriptItem],
    ) -> SimTurnRecord | None:
        if not config.auto_create_character:
            return None
        session_row = await self._event_store.get_session_row(session_id=config.session_id)
        if session_row is None:
            raise LookupError(f"session not found: {config.session_id}")
        prior_events = await self._event_store.list_events(session_id=config.session_id)
        state = self._reducer.replay(
            self._reducer.initial(
                session_id=config.session_id,
                system_id=session_row.system_id,
                adventure_id=session_row.adventure_id,
            ),
            prior_events,
        )
        if state.party:
            return None
        events = self._default_character_events(
            config=config,
            system_id=session_row.system_id,
            trace_id=trace_id,
        )
        if not events:
            return None
        await self._event_store.append_many(events)
        event_types = [event.event_type for event in events]
        action = SimulatedPlayerAction(
            action=f"按照 {session_row.system_id} 规则创建起始角色 {config.character_name}，然后再进入剧情。",
            intent="character_creation",
            confidence=1.0,
            public_rationale="真实跑团在进入剧情前需要先有玩家角色；后续检定与资源变化都必须引用角色状态。",
            private_reasoning="这是模拟器自动执行的开局准备步骤，不是普通剧情内玩家发言。",
            human_behavior_notes=["创建角色是跑团准备阶段，不是剧情内行动。"],
        )
        narration = _character_creation_narration(events)
        completion = CompletionAssessment(
            status="continue",
            confidence=1.0,
            public_rationale="角色已经创建并写入会话，模拟玩家可以进入开场剧情。",
            unresolved_goals=[],
        )
        row_id = await self._recorder.record_turn(
            run_id=run_id,
            turn_index=0,
            player_action=action,
            gm_result={"trace_id": trace_id, "intent": {"type": "character_creation"}, "narration": narration},
            committed_events=[event.model_dump(mode="json") for event in events],
            completion=completion,
            trace_id=trace_id,
        )
        transcript.append(
            SimTranscriptItem(
                turn_index=0,
                player_action=action.action,
                gm_response=narration,
                committed_event_types=event_types,
            )
        )
        return SimTurnRecord(
            id=row_id,
            run_id=run_id,
            turn_index=0,
            player_action=action,
            gm_response=narration,
            committed_event_types=event_types,
            trace_id=trace_id,
            completion=completion,
        )

    def _default_character_events(self, *, config: SimConfig, system_id: str, trace_id: str) -> list[DomainEvent]:
        if system_id != "coc7e":
            return []
        result = CocInvestigatorFactory().quick_fire(
            investigator_id=new_id("pc"),
            name=config.character_name,
            occupation=config.character_occupation,
            age=config.character_age,
            owner=config.actor_id,
            dice=DiceEngine(seed=config.character_seed),
            personal_interest_skills=["library_use", "spot_hidden", "listen", "dodge"],
        )
        return self._characters.create_character_events(
            session_id=config.session_id,
            character=result.character,
            trace_id=trace_id,
        )

    async def _player_visible_state(self, *, session_id: str) -> dict[str, Any]:
        session_row = await self._event_store.get_session_row(session_id=session_id)
        if session_row is None:
            return {}
        events = await self._event_store.list_events(session_id=session_id)
        state = self._reducer.replay(
            self._reducer.initial(
                session_id=session_id,
                system_id=session_row.system_id,
                adventure_id=session_row.adventure_id,
            ),
            events,
        )
        return {
            "system_id": state.system_id,
            "adventure_id": state.adventure_id,
            "workflow_phase": state.workflow_phase,
            "party": [character.model_dump(mode="json") for character in state.party],
            "discovered_clues": state.discovered_clues,
            "revealed_handouts": state.revealed_handouts,
            "current_units": state.current_units,
            "recent_event_types": [event.event_type for event in events[-8:]],
        }


def _character_creation_narration(events: list[DomainEvent]) -> str:
    created = [event for event in events if event.event_type == "CharacterCreated"]
    if not created:
        return "没有创建新的玩家角色。"
    payload = created[0].payload
    resources = payload.get("resources") if isinstance(payload, dict) else {}
    skills = payload.get("skills") if isinstance(payload, dict) else {}
    skill_items = skills if isinstance(skills, dict) else {}
    resource_items = resources if isinstance(resources, dict) else {}
    top_skills = sorted(
        [(key, value) for key, value in skill_items.items() if isinstance(value, int)],
        key=lambda item: item[1],
        reverse=True,
    )[:5]
    return (
        f"已完成起始调查员创建：{payload.get('name', '未命名角色')}。"
        f"核心资源：HP {resource_items.get('hp', '-')}, MP {resource_items.get('mp', '-')}, "
        f"SAN {resource_items.get('sanity', '-')}, Luck {resource_items.get('luck', '-')}。"
        f"主要技能：{', '.join(f'{name} {value}%' for name, value in top_skills) or '暂无'}。"
    )
