from __future__ import annotations

from chatrpg.ir.ruleset import RulesetIR
from chatrpg.ir.source import SourceBlock
from chatrpg.parsers.structured import StructuredExtractionRequest, StructuredExtractor


class RulesetCompiler:
    def __init__(self, extractor: StructuredExtractor) -> None:
        self._extractor = extractor

    async def compile(
        self,
        *,
        system_id: str,
        edition: str,
        blocks: list[SourceBlock],
        trace_id: str,
    ) -> RulesetIR:
        result = await self._extractor.extract(
            StructuredExtractionRequest(
                task=f"{system_id}.ruleset.compile",
                instructions=(
                    "Compile source blocks into RulesetIR. Extract rule atoms, executable procedures, "
                    "resolution kernels, tables, entities, and character schema. Keep rules source-backed "
                    "and do not copy large passages of copyrighted prose."
                ),
                blocks=blocks,
                output_schema=RulesetIR.model_json_schema(),
            ),
            trace_id=trace_id,
        )
        payload = {"system_id": system_id, "edition": edition, **result.payload}
        return RulesetIR.model_validate(payload)
