from __future__ import annotations

from collections import Counter
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
        handout_ids = {handout.id for handout in adventure.handouts}
        self._append_duplicate_issues(
            issues,
            kind="unit",
            ids=[unit.id for unit in adventure.units],
        )
        self._append_duplicate_issues(
            issues,
            kind="revelation",
            ids=[revelation.id for revelation in adventure.revelations],
        )
        self._append_duplicate_issues(
            issues,
            kind="clue",
            ids=[clue.id for clue in adventure.clues],
        )
        self._append_duplicate_issues(
            issues,
            kind="handout",
            ids=[handout.id for handout in adventure.handouts],
        )
        for revelation in adventure.revelations:
            for unit_id in revelation.unlocks:
                if unit_id not in unit_ids:
                    issues.append(
                        ValidationIssue(
                            code="missing_revelation_unlock",
                            subject=revelation.id,
                            message="Revelation unlocks a missing content unit.",
                        )
                    )
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
        for location in adventure.locations:
            for unit_id in location.unit_ids:
                if unit_id not in unit_ids:
                    issues.append(
                        ValidationIssue(
                            code="missing_location_unit",
                            subject=location.id,
                            message="Location references a missing content unit.",
                        )
                    )
            for exit_id in location.exits_to:
                if exit_id and exit_id not in {item.id for item in adventure.locations}:
                    issues.append(
                        ValidationIssue(
                            code="missing_location_exit",
                            subject=location.id,
                            message="Location exit points to a missing location.",
                        )
                    )
        for npc in adventure.npcs:
            for unit_id in npc.unit_ids:
                if unit_id not in unit_ids:
                    issues.append(
                        ValidationIssue(
                            code="missing_npc_unit",
                            subject=npc.id,
                            message="NPC references a missing content unit.",
                        )
                    )
        for encounter in adventure.encounters:
            for unit_id in encounter.unit_ids:
                if unit_id not in unit_ids:
                    issues.append(
                        ValidationIssue(
                            code="missing_encounter_unit",
                            subject=encounter.id,
                            message="Encounter references a missing content unit.",
                        )
                    )
        for timeline in adventure.timelines:
            for unlock_id in timeline.unlocks:
                if unlock_id not in unit_ids and unlock_id not in revelation_ids and unlock_id not in clue_ids and unlock_id not in handout_ids:
                    issues.append(
                        ValidationIssue(
                            code="missing_timeline_unlock",
                            subject=timeline.id,
                            message="Timeline unlock target is not present in the adventure IR.",
                        )
                    )
        return issues

    @staticmethod
    def _append_duplicate_issues(issues: list[ValidationIssue], *, kind: str, ids: list[str]) -> None:
        for item_id, count in Counter(ids).items():
            if count > 1:
                issues.append(
                    ValidationIssue(
                        code=f"duplicate_{kind}_id",
                        subject=item_id,
                        message=f"AdventureIR contains duplicate {kind} identifiers.",
                    )
                )


class RulesetIRValidator:
    def validate(self, ruleset: RulesetIR) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        kernel_ids = {
            str(kernel.get("id"))
            for kernel in ruleset.resolution_kernels
            if isinstance(kernel.get("id"), str)
        }
        procedure_ids = [procedure.id for procedure in ruleset.procedures]
        AdventureIRValidator._append_duplicate_issues(issues, kind="procedure", ids=procedure_ids)
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
