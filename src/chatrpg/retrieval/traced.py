from __future__ import annotations

from chatrpg.db.repositories import PostgresSemanticTraceStore
from chatrpg.retrieval.semantic import SemanticMatchRequest, SemanticMatchResult, SemanticMatcher


class TracedSemanticMatcher:
    def __init__(self, *, matcher: SemanticMatcher, trace_store: PostgresSemanticTraceStore) -> None:
        self._matcher = matcher
        self._trace_store = trace_store

    async def match(self, request: SemanticMatchRequest, *, trace_id: str) -> SemanticMatchResult:
        result = await self._matcher.match(request, trace_id=trace_id)
        await self._trace_store.record_match(request=request, result=result, trace_id=trace_id)
        return result
