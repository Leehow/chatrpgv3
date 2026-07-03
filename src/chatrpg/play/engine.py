from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.agents.contracts import AgentTraceStep, IntentFrame, NarrationRequest, NarrationResult
from chatrpg.agents.main_agent import PiMainAgent
from chatrpg.core.ids import new_id
from chatrpg.db.repositories import PostgresEventStore, PostgresIRStore, PostgresSemanticTraceStore
from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState
from chatrpg.ir.workflow import WorkflowPhaseSpec, WorkflowSpec
from chatrpg.play.agent_loop import AgentLoopEngine, AgentLoopRunRequest
from chatrpg.runtime.adventure import AdventureEngine, AdventureFrontier
from chatrpg.runtime.handouts import HandoutEngine
from chatrpg.runtime.state import StateReducer
from chatrpg.runtime.workflow import WorkflowEngine
from chatrpg.systems.coc7e.procedures import ProcedureExecutionResult


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
        max_agent_steps: int = 6,
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
        self._max_agent_steps = max_agent_steps

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
        self._append_trace(
            agent_trace,
            stage="启动 Agent Loop",
            summary="进入 ReAct 式工具循环：观察、决策、调用 Runtime 工具、观察结果，直到无需继续工具调用。",
            data={
                "system_id": session_row.system_id,
                "can_advance_adventure": can_advance_adventure,
                "max_agent_steps": self._max_agent_steps,
            },
        )
        loop_result = await AgentLoopEngine(
            agent=self._agent,
            semantic_matcher=self._semantic_matcher,
            semantic_trace_store=self._semantic_trace_store,
            adventure_engine=self._adventures,
            handout_engine=self._handouts,
            reducer=self._reducer,
            workflow_engine=self._workflow,
        ).run(
            AgentLoopRunRequest(
                session_id=session_id,
                system_id=session_row.system_id,
                player_message=message,
                trace_id=trace_id,
                actor_id=actor_id,
                state=state,
                adventure=adventure,
                frontier=frontier,
                workflow=workflow,
                can_advance_adventure=can_advance_adventure,
                max_steps=self._max_agent_steps,
            )
        )
        committed_events.extend(loop_result.committed_events)
        state = loop_result.state
        frontier = loop_result.frontier
        intent = loop_result.intent
        procedure_result = loop_result.procedure_result
        clue_decision = loop_result.clue_decision
        agent_trace.extend(loop_result.agent_trace)
        self._append_trace(
            agent_trace,
            stage="Agent Loop 结束",
            summary="工具循环完成，准备提交事件并生成玩家可见叙述。",
            data={
                "stop_reason": loop_result.stop_reason,
                "event_types": [event.event_type for event in loop_result.committed_events],
            },
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

    @staticmethod
    def _intent_with_bound_skill_call(intent: IntentFrame) -> IntentFrame:
        return AgentLoopEngine._intent_with_bound_skill_call(intent)

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
