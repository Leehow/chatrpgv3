from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.agents.contracts import IntentFrame, NarrationRequest, NarrationResult, PlayerInput
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
        intent = await self._agent.resolve_intent(
            PlayerInput(
                session_id=session_id,
                actor_id=actor_id,
                message=message,
                context=build_intent_context(
                    system_id=session_row.system_id,
                    phase=phase,
                    state=state,
                    adventure=adventure,
                    frontier=frontier,
                ),
            ),
            trace_id=trace_id,
        )
        intent = self._intent_with_bound_skill_call(intent)
        procedure_result = self._run_native_procedure(
            session_id=session_id,
            state=state,
            intent=intent,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        if procedure_result is not None and procedure_result.events:
            committed_events.extend(procedure_result.events)
            state = self._reducer.replay(state, procedure_result.events)
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
        if committed_events:
            await self._event_store.append_many(committed_events)
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
                ),
            ),
            trace_id=trace_id,
        )
        return PlayTurnResult(
            trace_id=trace_id,
            intent=intent,
            narration=narration,
            committed_events=committed_events,
            clue_decision=None if clue_decision is None else clue_decision.__dict__,
            procedure_result=None if procedure_result is None else procedure_result.model_dump(mode="json"),
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
