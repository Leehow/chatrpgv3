from __future__ import annotations

from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import KnownFact, SessionState


class KnowledgeEngine:
    def learn_fact_event(
        self,
        *,
        session_id: str,
        fact_id: str,
        known_by: str,
        confidence: str,
        source_event_id: str,
        trace_id: str,
    ) -> DomainEvent:
        fact = KnownFact(
            id=fact_id,
            known_by=known_by,
            confidence=confidence,
            source_event_id=source_event_id,
        )
        return DomainEvent(
            session_id=session_id,
            event_type="FactLearned",
            payload=fact.model_dump(mode="json"),
            trace_id=trace_id,
        )

    def knows(self, state: SessionState, *, fact_id: str, known_by: str) -> bool:
        for fact in state.known_facts:
            if fact.id == fact_id and fact.known_by == known_by:
                return True
        return False
