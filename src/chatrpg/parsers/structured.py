from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from chatrpg.agents.pi_client import PiClient, PiMessage
from chatrpg.ir.source import SourceBlock


class StructuredExtractionRequest(BaseModel):
    task: str
    instructions: str
    blocks: list[SourceBlock]
    output_schema: dict[str, Any]


class StructuredExtractionResult(BaseModel):
    task: str
    payload: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class StructuredExtractor(Protocol):
    async def extract(
        self,
        request: StructuredExtractionRequest,
        *,
        trace_id: str,
    ) -> StructuredExtractionResult: ...


class PiStructuredExtractor:
    def __init__(self, client: PiClient) -> None:
        self._client = client

    async def extract(
        self,
        request: StructuredExtractionRequest,
        *,
        trace_id: str,
    ) -> StructuredExtractionResult:
        messages = [
            PiMessage(
                role="system",
                content="Extract source-grounded TRPG data. Return schema-valid JSON only.",
            ),
            PiMessage(role="user", content=request.model_dump_json()),
        ]
        raw = await self._client.complete_json(
            task=request.task,
            messages=messages,
            json_schema=StructuredExtractionResult.model_json_schema(),
            trace_id=trace_id,
        )
        return StructuredExtractionResult.model_validate(raw)
