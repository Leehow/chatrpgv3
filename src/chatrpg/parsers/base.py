from __future__ import annotations

from pydantic import BaseModel

from chatrpg.ir.source import SourceBlock
from chatrpg.retrieval.semantic import SemanticCandidate, SemanticMatchRequest, SemanticMatcher


class BlockClassification(BaseModel):
    block_id: str
    label: str
    confidence: float
    rationale: str


class SemanticBlockClassifier:
    def __init__(self, matcher: SemanticMatcher) -> None:
        self._matcher = matcher

    async def classify(
        self,
        *,
        block: SourceBlock,
        taxonomy: list[SemanticCandidate],
        task: str,
        trace_id: str,
    ) -> BlockClassification:
        if block.text is None:
            return BlockClassification(block_id=block.id, label="unknown", confidence=0.0, rationale="empty")
        result = await self._matcher.match(
            SemanticMatchRequest(
                task=task,
                query=block.text,
                candidates=taxonomy,
                instructions="Select the best taxonomy item by meaning.",
            ),
            trace_id=trace_id,
        )
        if not result.choices:
            return BlockClassification(block_id=block.id, label="unknown", confidence=0.0, rationale="none")
        choice = result.choices[0]
        return BlockClassification(
            block_id=block.id,
            label=choice.candidate_id,
            confidence=choice.confidence,
            rationale=choice.rationale,
        )
