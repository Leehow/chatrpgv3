from __future__ import annotations

from chatrpg.core.ids import new_id
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState


class CombatSceneManager:
    def start_after_attack(
        self,
        *,
        session_id: str,
        state: SessionState,
        attack_event: DomainEvent,
        trace_id: str,
    ) -> list[DomainEvent]:
        target_actor_id = attack_event.payload.get("target_actor_id")
        if not isinstance(attack_event.actor_id, str) or not isinstance(target_actor_id, str):
            return []
        if attack_event.payload.get("dead") is True:
            return []
        participants = sorted({attack_event.actor_id, target_actor_id})
        existing = self._existing_combat_id(state=state, participants=participants)
        if existing is not None:
            return []
        combat_id = new_id("cmb")
        return [
            DomainEvent(
                session_id=session_id,
                event_type="CombatStarted",
                actor_id=attack_event.actor_id,
                payload={
                    "combat_id": combat_id,
                    "participants": participants,
                    "source_event_id": attack_event.id,
                    "reason": "hostile attack resolved by runtime",
                },
                trace_id=trace_id,
            )
        ]

    @staticmethod
    def _existing_combat_id(*, state: SessionState, participants: list[str]) -> str | None:
        target = set(participants)
        for item in state.active_combats:
            raw_participants = item.get("participants")
            combat_id = item.get("combat_id")
            if isinstance(raw_participants, list) and isinstance(combat_id, str):
                if target.issubset({str(participant) for participant in raw_participants}):
                    return combat_id
        return None
