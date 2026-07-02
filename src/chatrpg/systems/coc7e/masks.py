from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.validators import AdventureIRValidator, ValidationIssue
from chatrpg.parsers.adventure_compiler import AdventureCompiler
from chatrpg.parsers.structured import StructuredExtractionRequest, StructuredExtractionResult, StructuredExtractor
from chatrpg.ir.source import SourceBlock


class MasksCompileResult(BaseModel):
    adventure: AdventureIR
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MasksAdventureCompiler:
    def __init__(self, extractor: StructuredExtractor) -> None:
        self._extractor = extractor
        self._generic = AdventureCompiler(extractor)
        self._validator = AdventureIRValidator()

    async def compile(
        self,
        *,
        adventure_id: str,
        blocks: list[SourceBlock],
        trace_id: str,
    ) -> MasksCompileResult:
        base = await self._generic.compile(
            adventure_id=adventure_id,
            system_id="coc7e",
            title="Masks of Nyarlathotep",
            blocks=blocks,
            trace_id=trace_id,
        )
        enrichment = await self._extractor.extract(
            StructuredExtractionRequest(
                task="coc7e.masks.enrich",
                instructions=(
                    "Enrich the AdventureIR for a globe-spanning investigative campaign. Extract chapter/frontier "
                    "gateways, location units, NPC assets, clue carriers, handout assets, SAN triggers, tomes, spells, "
                    "artifacts, travel links, and outgoing leads. Preserve keeper-only information separately from "
                    "player-visible discoveries and keep all output source-grounded."
                ),
                blocks=blocks,
                output_schema=AdventureIR.model_json_schema(),
            ),
            trace_id=trace_id,
        )
        adventure = base.model_copy(update=enrichment.payload, deep=True)
        return MasksCompileResult(
            adventure=adventure,
            issues=self._validator.validate(adventure),
            warnings=enrichment.warnings,
        )
