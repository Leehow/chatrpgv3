from __future__ import annotations

from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.source import SourceBlock
from chatrpg.parsers.structured import StructuredExtractionRequest, StructuredExtractor


class AdventureCompiler:
    def __init__(self, extractor: StructuredExtractor) -> None:
        self._extractor = extractor

    async def compile(
        self,
        *,
        adventure_id: str,
        system_id: str,
        title: str,
        blocks: list[SourceBlock],
        trace_id: str,
    ) -> AdventureIR:
        result = await self._extractor.extract(
            StructuredExtractionRequest(
                task=f"{system_id}.adventure.compile",
                instructions=(
                    "Compile source blocks into AdventureIR. Extract content units, revelations, clue carriers, "
                    "NPCs, locations, encounters, handouts, and timelines. Preserve source references. Separate "
                    "player-visible information from keeper-only and runtime-only information."
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
        return AdventureIR.model_validate(payload)
