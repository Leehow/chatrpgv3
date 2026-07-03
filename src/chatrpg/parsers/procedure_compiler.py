from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.ruleset import ProcedureSpec
from chatrpg.ir.source import SourceBlock
from chatrpg.parsers.structured import StructuredExtractionRequest, StructuredExtractor


class ProcedureCompileResult(BaseModel):
    procedures: list[ProcedureSpec] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProcedureCompiler:
    def __init__(self, extractor: StructuredExtractor) -> None:
        self._extractor = extractor

    async def compile(self, *, system_id: str, blocks: list[SourceBlock], trace_id: str) -> ProcedureCompileResult:
        result = await self._extractor.extract(
            StructuredExtractionRequest(
                task=f"{system_id}.procedures.compile",
                instructions="Extract executable ProcedureSpec objects with inputs, rolls, resource changes, events, and source references.",
                blocks=blocks,
                output_schema=ProcedureCompileResult.model_json_schema(),
            ),
            trace_id=trace_id,
        )
        return ProcedureCompileResult.model_validate(result.payload)
