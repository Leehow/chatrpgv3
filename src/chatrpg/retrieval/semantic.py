from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field


class SemanticCandidate(BaseModel):
    id: str
    label: str
    description: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SemanticMatchRequest(BaseModel):
    task: str
    query: str
    candidates: list[SemanticCandidate]
    instructions: str
    confidence_floor: float = Field(default=0.70, ge=0.0, le=1.0)


class SemanticChoice(BaseModel):
    candidate_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class SemanticMatchResult(BaseModel):
    status: Literal["matched", "ambiguous", "no_match"]
    choices: list[SemanticChoice] = Field(default_factory=list)
    needs_human_review: bool = False


class SemanticMatcher(Protocol):
    async def match(self, request: SemanticMatchRequest, *, trace_id: str) -> SemanticMatchResult:
        pass
