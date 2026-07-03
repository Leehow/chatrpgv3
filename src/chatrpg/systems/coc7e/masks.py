from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.source import SourceBlock
from chatrpg.ir.validators import AdventureIRValidator, ValidationIssue
from chatrpg.parsers.adventure_compiler import AdventureCompiler
from chatrpg.parsers.structured import StructuredExtractionRequest, StructuredExtractor


class CampaignCompileResult(BaseModel):
    adventure: AdventureIR
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CampaignAdventureCompiler:
    def __init__(self, extractor: StructuredExtractor) -> None:
        self._extractor = extractor
        self._generic = AdventureCompiler(extractor)
        self._validator = AdventureIRValidator()

    async def compile(
        self,
        *,
        adventure_id: str,
        title: str,
        blocks: list[SourceBlock],
        trace_id: str,
    ) -> CampaignCompileResult:
        base = await self._generic.compile(
            adventure_id=adventure_id,
            system_id="coc7e",
            title=title,
            blocks=blocks,
            trace_id=trace_id,
        )
        enrichment = await self._extractor.extract(
            StructuredExtractionRequest(
                task="coc7e.campaign.enrich",
                instructions="Extract chapter gates, locations, NPCs, clues, handouts, leads, hazards, and keeper-only facts into AdventureIR.",
                blocks=blocks,
                output_schema=AdventureIR.model_json_schema(),
            ),
            trace_id=trace_id,
        )
        adventure = base.model_copy(update=enrichment.payload, deep=True)
        return CampaignCompileResult(adventure=adventure, issues=self._validator.validate(adventure), warnings=enrichment.warnings)
