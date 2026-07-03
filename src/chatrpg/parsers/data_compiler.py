from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.ruleset import RuleEntity, RuleTable
from chatrpg.ir.source import SourceBlock
from chatrpg.parsers.structured import StructuredExtractionRequest, StructuredExtractor


class RuleDataCompileResult(BaseModel):
    tables: list[RuleTable] = Field(default_factory=list)
    entities: list[RuleEntity] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RuleDataCompiler:
    def __init__(self, extractor: StructuredExtractor) -> None:
        self._extractor = extractor

    async def compile(self, *, system_id: str, blocks: list[SourceBlock], trace_id: str) -> RuleDataCompileResult:
        result = await self._extractor.extract(
            StructuredExtractionRequest(
                task=f"{system_id}.data.compile",
                instructions="Extract RuleTable and RuleEntity records with source references.",
                blocks=blocks,
                output_schema=RuleDataCompileResult.model_json_schema(),
            ),
            trace_id=trace_id,
        )
        return RuleDataCompileResult.model_validate(result.payload)
