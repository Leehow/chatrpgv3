from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from chatrpg.core.ids import new_id
from chatrpg.db.models import TraceSpanRow


class TraceWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def span(
        self,
        *,
        trace_id: str,
        name: str,
        kind: str,
        payload: dict[str, Any],
        parent_span_id: str | None = None,
    ) -> str:
        span_id = new_id("spn")
        self._session.add(
            TraceSpanRow(
                id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                kind=kind,
                name=name,
                payload=payload,
            )
        )
        return span_id
