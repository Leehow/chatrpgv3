from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from chatrpg.core.ids import new_id
from chatrpg.db.models import DomainEventRow, SemanticMatchRow, SessionRow
from chatrpg.ir.events import DomainEvent
from chatrpg.retrieval.semantic import SemanticMatchRequest, SemanticMatchResult


async def ping_postgres(session: AsyncSession) -> str:
    result = await session.execute(text("select version()"))
    return str(result.scalar_one())


class PostgresEventStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, *, system_id: str, adventure_id: str | None) -> str:
        session_id = new_id("ses")
        self._session.add(SessionRow(id=session_id, system_id=system_id, adventure_id=adventure_id, state={}))
        return session_id

    async def append(self, event: DomainEvent) -> None:
        self._session.add(
            DomainEventRow(
                id=event.id,
                session_id=event.session_id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                payload=event.payload,
                source_refs=[ref.model_dump(mode="json") for ref in event.source_refs],
                trace_id=event.trace_id,
            )
        )


class PostgresSemanticTraceStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_match(
        self,
        *,
        request: SemanticMatchRequest,
        result: SemanticMatchResult,
        trace_id: str,
    ) -> str:
        row_id = new_id("sem")
        self._session.add(
            SemanticMatchRow(
                id=row_id,
                task=request.task,
                request=request.model_dump(mode="json"),
                result=result.model_dump(mode="json"),
                trace_id=trace_id,
            )
        )
        return row_id
