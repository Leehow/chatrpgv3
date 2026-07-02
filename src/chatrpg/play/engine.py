from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.agents.contracts import (
    AgentTraceStep,
    IntentFrame,
    NarrationRequest,
    NarrationResult,
    PlayerInput,
)
from chatrpg.agents.main_agent import PiMainAgent
from chatrpg.core.ids import new_id
from chatrpg.db.repositories import PostgresEventStore, PostgresIRStore, PostgresSemanticTraceStore
from chatrpg.ir.adventure import AdventureIR, ClueCarrier, HandoutAsset
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState
from chatrpg.ir.workflow import WorkflowPhaseSpec, WorkflowSpec
from chatrpg.play.context import build_intent_context, procedure_passed
from chatrpg.retrieval.traced import TracedSemanticMatcher
from chatrpg.runtime.adventure import AdventureEngine, AdventureFrontier
from chatrpg.runtime.clues import ClueAcquisitionDecision, ClueAcquisitionEngine
from chatrpg.runtime.handouts import HandoutEngine
from chatrpg.runtime.state import StateReducer
from chatrpg.runtime.workflow import WorkflowEngine
from chatrpg.systems.coc7e.procedures import Coc7eProcedureRunner, ProcedureExecutionResult


class PlayTurnResult(BaseModel):
    trace_id: str
    intent: IntentFrame
    narration: NarrationResult
    committed_events: list[DomainEvent] = Field(default_factory=list)
    clue_decision: dict[str, object] | None = None
    procedure_result: dict[str, object] | None = None
    agent_trace: list[AgentTraceStep] = Field(default_factory=list)


class PlayEngine:
    def __init__(
        self,
        *,
        agent: PiMainAgent,
        event_store: PostgresEventStore,
        ir_store: PostgresIRStore,
        semantic_trace_store: PostgresSemanticTraceStore,
        semantic_matcher: object,
    ) -> None:
        self._agent = agent
        self._event_store = event_store
        self._ir_store = ir_store
        self._semantic_trace_store = semantic_trace_store
        self._semantic_matcher = semantic_matcher
        self._adventures = AdventureEngine()
        self._handouts = HandoutEngine()
        self._reducer = StateReducer()
        self._workflow = WorkflowEngine(self._reducer)

    async def turn(self, *, session_id: str, message: str, actor_id: str | None = None) -> PlayTurnResult:
        trace_id = new_id("trc")
        agent_trace: list[AgentTraceStep] = []
        session_row = await self._event_store.get_session_row(session_id=session_id)
        if session_row is None:
            raise LookupError(f"session not found: {session_id}")
        prior_events = await self._event_store.list_events(session_id=session_id)
        state = self._reducer.replay(
            self._reducer.initial(
                session_id=session_id,
                system_id=session_row.system_id,
                adventure_id=session_row.adventure_id,
            ),
            prior_events,
        )
        self._append_trace(
            agent_trace,
            stage="读取状态",
            summary="重放会话事件并构造当前 Runtime 状态。",
            data={
                "prior_event_count": len(prior_events),
                "party_size": len(state.party),
                "pending_decisions": len(state.pending_decisions),
                "pending_clues": len(state.pending_clues),
            },
        )
        adventure = await self._load_adventure(session_row.adventure_id)
        committed_events: list[DomainEvent] = []
        workflow = self._workflow.workflow_for(session_row.system_id)
        if workflow is not None:
            workflow_events = self._workflow.bootstrap_events(
                session_id=session_id,
                state=state,
                workflow=workflow,
                trace_id=trace_id,
            )
            if workflow_events:
                committed_events.extend(workflow_events)
                state = self._reducer.replay(state, workflow_events)
        frontier: AdventureFrontier | None = None
        can_advance_adventure = workflow is None or self._workflow.allows_adventure(state=state, workflow=workflow)
        if adventure is not None and can_advance_adventure:
            bootstrap_events = self._adventures.initial_frontier_events(
                session_id=session_id,
                adventure=adventure,
                state=state,
                trace_id=trace_id,
            )
            if bootstrap_events:
                committed_events.extend(bootstrap_events)
                state = self._reducer.replay(state, bootstrap_events)
            frontier = self._adventures.frontier(adventure=adventure, state=state)
        phase = None if workflow is None else self._workflow.current_phase(state=state, workflow=workflow)
        intent_context = build_intent_context(
            system_id=session_row.system_id,
            phase=phase,
            state=state,
            adventure=adventure,
            frontier=frontier,
        )
        self._append_trace(
            agent_trace,
            stage="构造上下文",
            summary="向 GM Agent 提供角色、进度、可用技能/工具、frontier 和待处理决策。",
            data={
                "system_id": session_row.system_id,
                "available_skills": len(intent_context.get("agent_skills", [])),
                "available_procedures": len(intent_context.get("available_procedures", [])),
                "pending_decisions": len(intent_context.get("pending_decisions", [])),
                "pending_clues": len(intent_context.get("pending_clues", [])),
            },
        )
        intent = await self._agent.resolve_intent(
            PlayerInput(
                session_id=session_id,
                actor_id=actor_id,
                message=message,
                context=intent_context,
            ),
            trace_id=trace_id,
        )
        self._append_trace(
            agent_trace,
            stage="分析玩家意图",
            summary="GM Agent 返回结构化 IntentFrame，不直接改状态或掷骰。",
            data={
                "intent": intent.intent,
                "procedure_id": intent.procedure_id,
                "skill_calls": [call.model_dump(mode="json") for call in intent.skill_calls],
                "needs_clarification": intent.needs_clarification,
            },
        )
        bound_intent = self._intent_with_bound_skill_call(intent)
        if bound_intent != intent:
            self._append_trace(
                agent_trace,
                stage="绑定技能工具",
                summary="将 GM Agent 选择的 procedure 型 skill_call 绑定为 Runtime procedure。",
                data={"procedure_id": bound_intent.procedure_id, "inputs": bound_intent.inputs},
            )
        intent = bound_intent
        procedure_result = self._run_native_procedure(
            session_id=session_id,
            state=state,
            intent=intent,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        if procedure_result is not None:
            self._append_trace(
                agent_trace,
                stage="调用规则工具",
                summary="Runtime 执行 procedure，并返回可提交的规则事件。",
                data={
                    "procedure_id": procedure_result.procedure_id,
                    "status": procedure_result.status,
                    "event_types": [event.event_type for event in procedure_result.events],
                    "message": procedure_result.message,
                },
            )
        if procedure_result is not None and procedure_result.events:
            committed_events.extend(procedure_result.events)
            state = self._reducer.replay(state, procedure_result.events)
        if adventure is not None and procedure_result is not None:
            pending_clue_events = self._pending_clue_events_after_successful_procedure(
                session_id=session_id,
                adventure=adventure,
                state=state,
                procedure_result=procedure_result,
                trace_id=trace_id,
            )
            if pending_clue_events:
                committed_events.extend(pending_clue_events)
                state = self._reducer.replay(state, pending_clue_events)
                frontier = self._adventures.frontier(adventure=adventure, state=state)
                self._append_trace(
                    agent_trace,
                    stage="兑现待处理线索",
                    summary="先前失败检定关联的线索在 Luck spend 成功后被提交。",
                    data={"event_types": [event.event_type for event in pending_clue_events]},
                )
        clue_decision: ClueAcquisitionDecision | None = None
        if adventure is not None and frontier is not None and can_advance_adventure:
            traced = TracedSemanticMatcher(
                matcher=self._semantic_matcher,
                trace_store=self._semantic_trace_store,
            )
            clue_decision = await ClueAcquisitionEngine(traced).select_clue(
                player_action=message,
                available_clues=list(frontier.clues),
                trace_id=trace_id,
            )
            self._append_trace(
                agent_trace,
                stage="匹配调查线索",
                summary="根据玩家行动和当前 frontier 进行线索语义匹配。",
                data={
                    "status": clue_decision.status,
                    "clue_id": None if clue_decision.clue is None else clue_decision.clue.id,
                },
            )
            if clue_decision.clue is not None and self._can_commit_clue(
                clue=clue_decision.clue,
                procedure_result=procedure_result,
            ):
                clue_events = self._adventures.clue_found_events(
                    session_id=session_id,
                    clue=clue_decision.clue,
                    adventure=adventure,
                    trace_id=trace_id,
                )
                committed_events.extend(clue_events)
                state = self._reducer.replay(state, clue_events)
                handout_events = self._reveal_linked_handouts(
                    session_id=session_id,
                    adventure=adventure,
                    reveal_targets=[clue_decision.clue.id, clue_decision.clue.revelation_id],
                    trace_id=trace_id,
                )
                if handout_events:
                    committed_events.extend(handout_events)
                    state = self._reducer.replay(state, handout_events)
                frontier = self._adventures.frontier(adventure=adventure, state=state)
            elif clue_decision.clue is not None:
                pending_event = self._pending_clue_event(
                    session_id=session_id,
                    clue=clue_decision.clue,
                    procedure_result=procedure_result,
                    trace_id=trace_id,
                )
                if pending_event is not None:
                    committed_events.append(pending_event)
                    state = self._reducer.apply(state, pending_event)
                    self._append_trace(
                        agent_trace,
                        stage="暂存线索机会",
                        summary="线索匹配成功但规则检定失败，保存为可由 Luck spend 兑现的待处理线索。",
                        data=pending_event.payload,
                    )
        if committed_events:
            await self._event_store.append_many(committed_events)
        self._append_trace(
            agent_trace,
            stage="提交事件",
            summary="将本回合所有 Runtime 事件写入事件流。",
            data={"event_types": [event.event_type for event in committed_events]},
        )
        narration = await self._agent.narrate(
            NarrationRequest(
                session_id=session_id,
                committed_events=[event.model_dump(mode="json") for event in [*prior_events, *committed_events]],
                visible_facts=self._visible_facts(
                    intent=intent,
                    state=state,
                    adventure=adventure,
                    frontier=frontier,
                    workflow=workflow,
                    procedure_result=procedure_result,
                    agent_trace=agent_trace,
                ),
            ),
            trace_id=trace_id,
        )
        self._append_trace(
            agent_trace,
            stage="生成叙述",
            summary="Narrator 只根据已提交事件和玩家可见事实生成回应。",
            data={"narration_length": len(narration.text)},
        )
        return PlayTurnResult(
            trace_id=trace_id,
            intent=intent,
            narration=narration,
            committed_events=committed_events,
            clue_decision=None if clue_decision is None else clue_decision.__dict__,
            procedure_result=None if procedure_result is None else procedure_result.model_dump(mode="json"),
            agent_trace=agent_trace,
        )

    async def _load_adventure(self, adventure_id: str | None) -> AdventureIR | None:
        if adventure_id is None:
            return None
        return await self._ir_store.get_adventure(adventure_id=adventure_id)

    def _visible_facts(
        self,
        *,
        intent: IntentFrame,
        state: SessionState,
        adventure: AdventureIR | None,
        frontier: AdventureFrontier | None,
        workflow: WorkflowSpec | None,
        procedure_result: ProcedureExecutionResult | None,
        agent_trace: list[AgentTraceStep],
    ) -> list[dict[str, object]]:
        facts = [intent.model_dump(mode="json")]
        phase = None if workflow is None else self._workflow.current_phase(state=state, workflow=workflow)
        if phase is not None:
            facts.append(self._workflow_fact(phase=phase, state=state))
        if procedure_result is not None:
            facts.append(
                {
                    "type": "procedure_result",
                    "procedure_id": procedure_result.procedure_id,
                    "status": procedure_result.status,
                    "message": procedure_result.message,
                    "events": [event.model_dump(mode="json") for event in procedure_result.events],
                }
            )
        facts.append(
            {
                "type": "agent_trace",
                "steps": [step.model_dump(mode="json") for step in agent_trace],
            }
        )
        if state.party:
            facts.append(
                {
                    "type": "party_status",
                    "characters": [
                        {
                            "id": character.id,
                            "name": character.name,
                            "owner": character.owner,
                            "resources": character.resources,
                            "traits": character.traits,
                            "skills": character.skills,
                            "conditions": character.conditions,
                        }
                        for character in state.party
                    ],
                }
            )
        if adventure is None or frontier is None:
            return facts
        unit_ids = {unit.id for unit in frontier.units if unit.visibility == "player_visible"}
        if not unit_ids:
            return facts
        facts.append(
            {
                "type": "adventure_frontier",
                "adventure_id": adventure.adventure_id,
                "title": adventure.title,
                "units": [
                    unit.model_dump(mode="json")
                    for unit in frontier.units
                    if unit.visibility == "player_visible"
                ],
                "locations": [
                    {
                        "id": location.id,
                        "name": location.name,
                        "summary": location.summary,
                        "unit_ids": location.unit_ids,
                    }
                    for location in adventure.locations
                    if unit_ids.intersection(location.unit_ids)
                ],
                "npcs": [
                    {
                        "id": npc.id,
                        "name": npc.name,
                        "summary": npc.summary,
                        "public_profile": npc.public_profile,
                        "unit_ids": npc.unit_ids,
                    }
                    for npc in adventure.npcs
                    if unit_ids.intersection(npc.unit_ids)
                ],
            }
        )
        return facts

    @staticmethod
    def _workflow_fact(*, phase: WorkflowPhaseSpec, state: SessionState) -> dict[str, object]:
        return {
            "type": "workflow_state",
            "phase_id": phase.id,
            "phase_label": phase.label,
            "phase_kind": phase.kind,
            "allows_adventure": phase.allows_adventure,
            "requires_character_creation": phase.kind == "character_creation" and not state.party,
            "completed_phase_ids": state.completed_workflow_phases,
        }

    def _reveal_linked_handouts(
        self,
        *,
        session_id: str,
        adventure: AdventureIR,
        reveal_targets: list[str],
        trace_id: str,
    ) -> list[DomainEvent]:
        revealed: list[DomainEvent] = []
        target_set = set(reveal_targets)
        for handout in adventure.handouts:
            if self._handout_reveals_any(handout, target_set):
                revealed.append(self._handouts.reveal_event(session_id=session_id, handout=handout, trace_id=trace_id))
        return revealed

    @staticmethod
    def _handout_reveals_any(handout: HandoutAsset, reveal_targets: set[str]) -> bool:
        return bool(set(handout.reveals).intersection(reveal_targets))

    @staticmethod
    def _run_native_procedure(
        *,
        session_id: str,
        state: SessionState,
        intent: IntentFrame,
        actor_id: str | None,
        trace_id: str,
    ) -> ProcedureExecutionResult | None:
        if intent.procedure_id is None:
            return None
        resolved_actor_id = actor_id or intent.actor_id or (state.party[0].id if state.party else None)
        if state.system_id == "coc7e":
            return Coc7eProcedureRunner().run(
                procedure_id=intent.procedure_id,
                session_id=session_id,
                state=state,
                actor_id=resolved_actor_id,
                inputs=intent.inputs,
                trace_id=trace_id,
            )
        return ProcedureExecutionResult(
            procedure_id=intent.procedure_id,
            status="unsupported",
            message="No native procedure runner is registered for this system.",
        )

    @staticmethod
    def _intent_with_bound_skill_call(intent: IntentFrame) -> IntentFrame:
        if intent.procedure_id is not None or not intent.skill_calls:
            return intent
        best_call = max(intent.skill_calls, key=lambda item: item.confidence)
        if best_call.tool_kind != "procedure" or best_call.procedure_id is None:
            return intent
        return intent.model_copy(
            update={
                "procedure_id": best_call.procedure_id,
                "inputs": best_call.inputs,
                "confidence": min(intent.confidence, best_call.confidence),
            }
        )

    @staticmethod
    def _can_commit_clue(*, clue: ClueCarrier, procedure_result: ProcedureExecutionResult | None) -> bool:
        if not clue.suggested_skills:
            return True
        if procedure_result is None or procedure_result.status != "completed":
            return False
        return procedure_passed(procedure_result.events) is True

    @staticmethod
    def _source_roll_event_id(procedure_result: ProcedureExecutionResult | None) -> str | None:
        if procedure_result is None:
            return None
        for event in procedure_result.events:
            if event.event_type in {"SkillRollResolved", "PushedRollResolved"}:
                return event.id
            if event.event_type == "LuckSpent":
                value = event.payload.get("source_event_id")
                return value if isinstance(value, str) else event.id
        return None

    @staticmethod
    def _procedure_passed(procedure_result: ProcedureExecutionResult | None) -> bool:
        if procedure_result is None or procedure_result.status != "completed":
            return False
        return procedure_passed(procedure_result.events) is True

    def _pending_clue_event(
        self,
        *,
        session_id: str,
        clue: ClueCarrier,
        procedure_result: ProcedureExecutionResult | None,
        trace_id: str,
    ) -> DomainEvent | None:
        if procedure_result is None or procedure_result.status != "completed":
            return None
        if self._procedure_passed(procedure_result):
            return None
        source_event_id = self._source_roll_event_id(procedure_result)
        if source_event_id is None:
            return None
        return DomainEvent(
            session_id=session_id,
            event_type="CluePending",
            payload={
                "clue_id": clue.id,
                "revelation_id": clue.revelation_id,
                "source_event_id": source_event_id,
                "reason": "matched clue gated by failed roll",
            },
            source_refs=clue.source_refs,
            trace_id=trace_id,
        )

    def _pending_clue_events_after_successful_procedure(
        self,
        *,
        session_id: str,
        adventure: AdventureIR,
        state: SessionState,
        procedure_result: ProcedureExecutionResult,
        trace_id: str,
    ) -> list[DomainEvent]:
        if not self._procedure_passed(procedure_result):
            return []
        source_event_id = self._source_roll_event_id(procedure_result)
        events: list[DomainEvent] = []
        pending_items = [
            item
            for item in state.pending_clues
            if source_event_id is None or item.get("source_event_id") == source_event_id
        ]
        for pending in pending_items:
            clue_id = pending.get("clue_id")
            clue = next((item for item in adventure.clues if item.id == clue_id), None)
            if clue is None or clue.id in state.discovered_clues:
                continue
            events.extend(
                self._adventures.clue_found_events(
                    session_id=session_id,
                    clue=clue,
                    adventure=adventure,
                    trace_id=trace_id,
                )
            )
            events.append(
                DomainEvent(
                    session_id=session_id,
                    event_type="PendingClueResolved",
                    payload={"clue_id": clue.id, "source_event_id": pending.get("source_event_id")},
                    trace_id=trace_id,
                )
            )
        return events

    @staticmethod
    def _append_trace(
        steps: list[AgentTraceStep],
        *,
        stage: str,
        summary: str,
        data: dict[str, object] | None = None,
    ) -> None:
        steps.append(
            AgentTraceStep(
                step=len(steps) + 1,
                stage=stage,
                summary=summary,
                data={} if data is None else data,
            )
        )
