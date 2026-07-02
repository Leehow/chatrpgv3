from __future__ import annotations

from chatrpg.core.ids import new_id
from chatrpg.play import PlayEngine
from chatrpg.sim.models import (
    CompletionAssessment,
    PlayerPersona,
    SimConfig,
    SimPlayerObservation,
    SimRunSummary,
    SimTranscriptItem,
    SimTurnRecord,
)
from chatrpg.sim.player import SimulatedPlayerAgent
from chatrpg.sim.recorder import SimulationRecorder
from chatrpg.sim.report import SimulationReportBuilder


class SimulationRunner:
    def __init__(
        self,
        *,
        player: SimulatedPlayerAgent,
        gm: PlayEngine,
        recorder: SimulationRecorder,
        reporter: SimulationReportBuilder | None = None,
    ) -> None:
        self._player = player
        self._gm = gm
        self._recorder = recorder
        self._reporter = reporter or SimulationReportBuilder()

    async def run(self, *, config: SimConfig, persona: PlayerPersona) -> SimRunSummary:
        trace_id = new_id("trc")
        run_id = await self._recorder.start_run(config=config, persona=persona, trace_id=trace_id)
        transcript: list[SimTranscriptItem] = []
        records: list[SimTurnRecord] = []
        final_assessment: CompletionAssessment | None = None
        for turn_index in range(1, config.max_turns + 1):
            observation = SimPlayerObservation(
                session_id=config.session_id,
                turn_index=turn_index,
                persona=persona,
                transcript=transcript,
                last_gm_response=None if not transcript else transcript[-1].gm_response,
                known_objectives=persona.goals,
            )
            action = await self._player.choose_action(observation, trace_id=trace_id)
            if action.wants_to_stop:
                final_assessment = CompletionAssessment(
                    status="completed",
                    confidence=action.confidence,
                    public_rationale=action.stop_reason or action.public_rationale,
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
                    public_rationale="Minimum turn count has not yet been reached.",
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
        report_markdown = self._reporter.build_markdown(run=loaded_run or {}, turns=loaded_turns)
        report_json = self._reporter.build_json(run=loaded_run or {}, turns=loaded_turns, markdown=report_markdown)
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
