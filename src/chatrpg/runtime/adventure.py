from __future__ import annotations

from dataclasses import dataclass

from chatrpg.core.ids import new_id
from chatrpg.ir.adventure import AdventureIR, ClueCarrier, ContentUnit, Revelation
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState


@dataclass(frozen=True)
class AdventureFrontier:
    units: tuple[ContentUnit, ...]
    revelations: tuple[Revelation, ...]
    clues: tuple[ClueCarrier, ...]


class AdventureEngine:
    def frontier(self, *, adventure: AdventureIR, state: SessionState) -> AdventureFrontier:
        unit_ids = set(state.unlocked_frontier)
        known_fact_ids = {fact.id for fact in state.known_facts}
        units = tuple(unit for unit in adventure.units if unit.id in unit_ids)
        revelations = tuple(revelation for revelation in adventure.revelations if revelation.id in known_fact_ids)
        clues = tuple(clue for clue in adventure.clues if clue.unit_id in unit_ids)
        return AdventureFrontier(units=units, revelations=revelations, clues=clues)

    def unlock_unit_event(self, *, session_id: str, unit_id: str, trace_id: str) -> DomainEvent:
        return DomainEvent(
            id=new_id("evt"),
            session_id=session_id,
            event_type="FrontierUnlocked",
            payload={"unit_id": unit_id},
            trace_id=trace_id,
        )

    def clue_found_events(
        self,
        *,
        session_id: str,
        clue: ClueCarrier,
        trace_id: str,
    ) -> list[DomainEvent]:
        return [
            DomainEvent(
                session_id=session_id,
                event_type="ClueDiscovered",
                payload={"clue_id": clue.id, "revelation_id": clue.revelation_id},
                source_refs=clue.source_refs,
                trace_id=trace_id,
            ),
            DomainEvent(
                session_id=session_id,
                event_type="FactLearned",
                payload={
                    "id": clue.revelation_id,
                    "known_by": "player_group",
                    "confidence": "confirmed",
                    "source_event_id": clue.id,
                },
                source_refs=clue.source_refs,
                trace_id=trace_id,
            ),
        ]
