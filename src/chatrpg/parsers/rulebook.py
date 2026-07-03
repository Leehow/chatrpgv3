from __future__ import annotations

from chatrpg.core.ids import new_id
from chatrpg.ir.ruleset import RuleAtom, RulesetIR
from chatrpg.ir.source import SourceBlock
from chatrpg.parsers.base import SemanticBlockClassifier
from chatrpg.parsers.taxonomies import RULEBOOK_BLOCK_TAXONOMY


class RulebookParser:
    def __init__(self, classifier: SemanticBlockClassifier) -> None:
        self._classifier = classifier

    async def parse_blocks(
        self,
        *,
        system_id: str,
        edition: str,
        blocks: list[SourceBlock],
        trace_id: str,
    ) -> RulesetIR:
        atoms: list[RuleAtom] = []
        for block in blocks:
            classification = await self._classifier.classify(
                block=block,
                taxonomy=RULEBOOK_BLOCK_TAXONOMY,
                task=f"{system_id}.rulebook.block.classify",
                trace_id=trace_id,
            )
            atoms.append(
                RuleAtom(
                    id=new_id("rat"),
                    system_id=system_id,
                    name=f"{system_id}:{block.id}",
                    kind=classification.label,
                    summary=classification.rationale,
                    source_refs=[block.source_ref()],
                )
            )
        return RulesetIR(
            system_id=system_id,
            edition=edition,
            rule_atoms=atoms,
            source_refs=[block.source_ref() for block in blocks],
        )
