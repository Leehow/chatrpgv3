from __future__ import annotations

from chatrpg.ir.adventure import AdventureIR, HandoutAsset
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState


class HandoutEngine:
    def reveal_event(self, *, session_id: str, handout: HandoutAsset, trace_id: str) -> DomainEvent:
        return DomainEvent(
            session_id=session_id,
            event_type="HandoutRevealed",
            payload={"handout_id": handout.id, "reveals": handout.reveals},
            source_refs=handout.source_refs,
            trace_id=trace_id,
        )

    def visible_handouts(self, *, adventure: AdventureIR, state: SessionState) -> list[HandoutAsset]:
        revealed = set(state.revealed_handouts)
        return [handout for handout in adventure.handouts if handout.id in revealed]
