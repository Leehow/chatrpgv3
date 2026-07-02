from __future__ import annotations

from dataclasses import dataclass

from chatrpg.ir.ruleset import ProcedureSpec, RuleAtom, RulesetIR


@dataclass(frozen=True)
class RuleLookupResult:
    rule_atoms: tuple[RuleAtom, ...]
    procedures: tuple[ProcedureSpec, ...]


class RulesEngine:
    def procedure(self, *, ruleset: RulesetIR, procedure_id: str) -> ProcedureSpec | None:
        for procedure in ruleset.procedures:
            if procedure.id == procedure_id:
                return procedure
        return None

    def by_applies_to(self, *, ruleset: RulesetIR, applies_to: str) -> RuleLookupResult:
        atoms = tuple(atom for atom in ruleset.rule_atoms if applies_to in atom.applies_to)
        procedures = tuple(procedure for procedure in ruleset.procedures if applies_to in procedure.inputs)
        return RuleLookupResult(rule_atoms=atoms, procedures=procedures)
