from __future__ import annotations

from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState


class StateReducer:
    def initial(self, *, session_id: str, system_id: str, adventure_id: str | None = None) -> SessionState:
        return SessionState(id=session_id, system_id=system_id, adventure_id=adventure_id)

    def apply(self, state: SessionState, event: DomainEvent) -> SessionState:
        next_state = state.model_copy(deep=True)
        if event.event_type == "FrontierUnlocked":
            value = event.payload.get("unit_id")
            if isinstance(value, str) and value not in next_state.unlocked_frontier:
                next_state.unlocked_frontier.append(value)
        if event.event_type == "ProcedureStarted":
            next_state.active_procedures.append(event.payload)
        return next_state

    def replay(self, state: SessionState, events: list[DomainEvent]) -> SessionState:
        current = state
        for event in events:
            current = self.apply(current, event)
        return current
