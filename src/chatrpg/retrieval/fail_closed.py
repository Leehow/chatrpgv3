from __future__ import annotations

from chatrpg.retrieval.semantic import SemanticMatchRequest, SemanticMatchResult


class SemanticGatewayNotConfigured(RuntimeError):
    pass


class FailClosedSemanticMatcher:
    async def match(self, request: SemanticMatchRequest, *, trace_id: str) -> SemanticMatchResult:
        raise SemanticGatewayNotConfigured("Configure the semantic gateway before parsing prose.")
