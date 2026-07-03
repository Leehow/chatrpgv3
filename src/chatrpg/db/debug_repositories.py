from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from chatrpg.core.ids import new_id
from chatrpg.db.models import LlmCallRow, ParserRunRow


class PostgresParserRunStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, *, document_id: str, profile: str, payload: dict[str, Any], trace_id: str) -> str:
        run_id = new_id("run")
        self._session.add(
            ParserRunRow(
                id=run_id,
                document_id=document_id,
                profile=profile,
                status="started",
                input=payload,
                output={},
                warnings=[],
                trace_id=trace_id,
            )
        )
        return run_id


class PostgresLlmCallStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        trace_id: str,
        task: str,
        model: str,
        request: dict[str, Any],
        response: dict[str, Any],
        status: str,
    ) -> str:
        row_id = new_id("llm")
        self._session.add(
            LlmCallRow(
                id=row_id,
                trace_id=trace_id,
                task=task,
                model=model,
                request=request,
                response=response,
                status=status,
            )
        )
        return row_id
