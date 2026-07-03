from __future__ import annotations

from chatrpg.agents.pi_client import PiClient, PiMessage
from chatrpg.retrieval.semantic import SemanticMatchRequest, SemanticMatchResult


class PiSemanticMatcher:
    def __init__(self, client: PiClient) -> None:
        self._client = client

    async def match(self, request: SemanticMatchRequest, *, trace_id: str) -> SemanticMatchResult:
        schema = SemanticMatchResult.model_json_schema()
        messages = [
            PiMessage(
                role="system",
                content="You are a semantic matcher for a TRPG parser/runtime. Return schema-valid JSON.",
            ),
            PiMessage(role="user", content=request.model_dump_json()),
        ]
        raw = await self._client.complete_json(
            task=request.task,
            messages=messages,
            json_schema=schema,
            trace_id=trace_id,
        )
        return SemanticMatchResult.model_validate(raw)
