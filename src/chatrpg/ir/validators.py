from __future__ import annotations

from dataclasses import dataclass

from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.ruleset import RulesetIR


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    subject: str
    message: str


class AdventureIRValidator:
    def validate(self, adventure: AdventureIR) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        unit_ids = {unit.id for unit in adventure.units}
        revelation_ids = {revelation.id for revelation in adventure.revelations}
        clue_ids = {clue.id for clue in adventure.clues}
        for clue in adventure.clues:
            if clue.unit_id not in unit_ids:
                issues.append(
                    ValidationIssue(
                        code="missing_clue_unit",
                        subject=clue.id,
                        message="Clue carrier references a missing content unit.",
                    )
                )
            if clue.revelation_id not in revelation_ids:
                issues.append(
                    ValidationIssue(
                        code="missing_clue_revelation",
                        subject=clue.id,
                        message="Clue carrier references a missing revelation.",
                    )
                )
        for handout in adventure.handouts:
            for reveal_id in handout.reveals:
                if reveal_id not in revelation_ids and reveal_id not in clue_ids and reveal_id not in unit_ids:
                    issues.append(
                        ValidationIssue(
                            code="missing_handout_reveal",
                            subject=handout.id,
                            message="Handout reveal target is not present in the adventure IR.",
                        )
                    )
        return issues


class RulesetIRValidator:
    def validate(self, ruleset: RulesetIR) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        kernel_ids = {
            str(kernel.get("id"))
            for kernel in ruleset.resolution_kernels
            if isinstance(kernel.get("id"), str)
        }
        for procedure in ruleset.procedures:
            for roll in procedure.rolls:
                if roll.kernel_id not in kernel_ids:
                    issues.append(
                        ValidationIssue(
                            code="missing_roll_kernel",
                            subject=procedure.id,
                            message="Procedure roll references a missing resolution kernel.",
                        )
                    )
        return issues
