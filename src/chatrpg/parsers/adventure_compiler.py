from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.source import SourceBlock
from chatrpg.ir.validators import AdventureIRValidator, ValidationIssue
from chatrpg.parsers.structured import StructuredExtractionRequest, StructuredExtractor


class ValidatedAdventureCompileResult(BaseModel):
    adventure: AdventureIR
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AdventureCompiler:
    def __init__(self, extractor: StructuredExtractor) -> None:
        self._extractor = extractor
        self._validator = AdventureIRValidator()

    async def compile(
        self,
        *,
        adventure_id: str,
        system_id: str,
        title: str,
        blocks: list[SourceBlock],
        trace_id: str,
    ) -> AdventureIR:
        result = await self.compile_validated(
            adventure_id=adventure_id,
            system_id=system_id,
            title=title,
            blocks=blocks,
            trace_id=trace_id,
        )
        return result.adventure

    async def compile_validated(
        self,
        *,
        adventure_id: str,
        system_id: str,
        title: str,
        blocks: list[SourceBlock],
        trace_id: str,
    ) -> ValidatedAdventureCompileResult:
        result = await self._extractor.extract(
            StructuredExtractionRequest(
                task=f"{system_id}.adventure.compile",
                instructions=(
                    "Compile source blocks into AdventureIR. Extract content units, revelations, clue carriers, "
                    "NPCs, locations, encounters, handouts, and timelines. Preserve source references. Separate "
                    "player-visible information from keeper-only and runtime-only information. All clue carriers must "
                    "reference existing content units and revelations; all unlocks must point to existing units."
                ),
                blocks=blocks,
                output_schema=AdventureIR.model_json_schema(),
            ),
            trace_id=trace_id,
        )
        payload = {
            "adventure_id": adventure_id,
            "system_id": system_id,
            "title": title,
            **result.payload,
        }
        adventure = AdventureIR.model_validate(payload)
        return ValidatedAdventureCompileResult(
            adventure=adventure,
            issues=self._validator.validate(adventure),
            warnings=result.warnings,
        )
