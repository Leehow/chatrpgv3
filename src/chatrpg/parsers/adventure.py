from __future__ import annotations

from chatrpg.ir.adventure import AdventureIR, ContentUnit
from chatrpg.ir.source import SourceBlock
from chatrpg.parsers.base import SemanticBlockClassifier
from chatrpg.parsers.taxonomies import ADVENTURE_BLOCK_TAXONOMY


class AdventureParser:
    def __init__(self, classifier: SemanticBlockClassifier) -> None:
        self._classifier = classifier

    async def parse_blocks(
        self,
        *,
        adventure_id: str,
        system_id: str,
        title: str,
        blocks: list[SourceBlock],
        trace_id: str,
    ) -> AdventureIR:
        units: list[ContentUnit] = []
        for block in blocks:
            classification = await self._classifier.classify(
                block=block,
                taxonomy=ADVENTURE_BLOCK_TAXONOMY,
                task=f"{system_id}.adventure.block.classify",
                trace_id=trace_id,
            )
            units.append(
                ContentUnit(
                    id=f"unit:{block.id}",
                    adventure_id=adventure_id,
                    kind=classification.label,
                    title=f"{title} source block",
                    summary=classification.rationale,
                    visibility="keeper_only",
                    source_refs=[block.source_ref()],
                )
            )
        return AdventureIR(
            adventure_id=adventure_id,
            system_id=system_id,
            title=title,
            units=units,
            source_refs=[block.source_ref() for block in blocks],
        )
