from __future__ import annotations

from chatrpg.core.ids import new_id
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState, SessionState


class CharacterEngine:
    def create_character_events(
        self,
        *,
        session_id: str,
        character: CharacterState,
        trace_id: str,
    ) -> list[DomainEvent]:
        return [
            DomainEvent(
                id=new_id("evt"),
                session_id=session_id,
                event_type="CharacterCreated",
                actor_id=character.id,
                payload=character.model_dump(mode="json"),
                trace_id=trace_id,
            )
        ]

    def change_resource_event(
        self,
        *,
        session_id: str,
        actor_id: str,
        resource_id: str,
        delta: int,
        reason: str,
        trace_id: str,
    ) -> DomainEvent:
        return DomainEvent(
            session_id=session_id,
            event_type="CharacterResourceChanged",
            actor_id=actor_id,
            payload={"resource_id": resource_id, "delta": delta, "reason": reason},
            trace_id=trace_id,
        )

    def find_character(self, state: SessionState, character_id: str) -> CharacterState | None:
        for character in state.party:
            if character.id == character_id:
                return character
        return None
