from __future__ import annotations

from chatrpg.core.ids import new_id
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState
from chatrpg.ir.workflow import WorkflowPhaseSpec, WorkflowSpec, WorkflowTransitionSpec
from chatrpg.runtime.state import StateReducer
from chatrpg.systems.workflows import workflow_for_system


class WorkflowEngine:
    def __init__(self, reducer: StateReducer | None = None) -> None:
        self._reducer = reducer or StateReducer()

    def workflow_for(self, system_id: str) -> WorkflowSpec | None:
        return workflow_for_system(system_id)

    def bootstrap_events(
        self,
        *,
        session_id: str,
        state: SessionState,
        workflow: WorkflowSpec,
        trace_id: str,
    ) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        current = state
        if current.workflow_phase is None:
            event = self.enter_phase_event(
                session_id=session_id,
                phase_id=workflow.initial_phase_id,
                trace_id=trace_id,
            )
            events.append(event)
            current = self._reducer.apply(current, event)
        while True:
            transition = self._next_automatic_transition(workflow=workflow, state=current)
            if transition is None:
                break
            completed = self.complete_phase_event(
                session_id=session_id,
                phase_id=transition.from_phase_id,
                trace_id=trace_id,
            )
            entered = self.enter_phase_event(
                session_id=session_id,
                phase_id=transition.to_phase_id,
                trace_id=trace_id,
                transition_id=transition.id,
            )
            events.extend([completed, entered])
            current = self._reducer.apply(self._reducer.apply(current, completed), entered)
        return events

    def current_phase(self, *, state: SessionState, workflow: WorkflowSpec) -> WorkflowPhaseSpec | None:
        if state.workflow_phase is None:
            return workflow.phase_by_id(workflow.initial_phase_id)
        return workflow.phase_by_id(state.workflow_phase)

    def allows_adventure(self, *, state: SessionState, workflow: WorkflowSpec) -> bool:
        phase = self.current_phase(state=state, workflow=workflow)
        return False if phase is None else phase.allows_adventure

    @staticmethod
    def enter_phase_event(
        *,
        session_id: str,
        phase_id: str,
        trace_id: str,
        transition_id: str | None = None,
    ) -> DomainEvent:
        payload: dict[str, object] = {"phase_id": phase_id}
        if transition_id is not None:
            payload["transition_id"] = transition_id
        return DomainEvent(
            id=new_id("evt"),
            session_id=session_id,
            event_type="WorkflowPhaseEntered",
            payload=payload,
            trace_id=trace_id,
        )

    @staticmethod
    def complete_phase_event(*, session_id: str, phase_id: str, trace_id: str) -> DomainEvent:
        return DomainEvent(
            id=new_id("evt"),
            session_id=session_id,
            event_type="WorkflowPhaseCompleted",
            payload={"phase_id": phase_id},
            trace_id=trace_id,
        )

    def _next_automatic_transition(
        self,
        *,
        workflow: WorkflowSpec,
        state: SessionState,
    ) -> WorkflowTransitionSpec | None:
        if state.workflow_phase is None:
            return None
        for transition in workflow.outgoing(state.workflow_phase):
            if transition.automatic and self._guard_passes(transition=transition, state=state):
                return transition
        return None

    @staticmethod
    def _guard_passes(*, transition: WorkflowTransitionSpec, state: SessionState) -> bool:
        if transition.guard == "always":
            return True
        if transition.guard == "party_exists":
            return bool(state.party)
        return False
