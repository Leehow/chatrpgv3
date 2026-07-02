from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.character_template import CharacterTemplate
from chatrpg.ir.state import CharacterState
from chatrpg.runtime.formulas import FormulaEvaluator


class CharacterCreationInput(BaseModel):
    character_id: str
    name: str
    owner: str | None = None
    fields: dict[str, int | str] = Field(default_factory=dict)
    skills: dict[str, int] = Field(default_factory=dict)
    conditions: list[str] = Field(default_factory=list)


class CharacterCreationAudit(BaseModel):
    formula_id: str
    target_id: str
    value: int | str
    dependencies: list[str] = Field(default_factory=list)


class CharacterCreationResult(BaseModel):
    character: CharacterState
    audit: list[CharacterCreationAudit] = Field(default_factory=list)


class CharacterCreationEngine:
    def __init__(self, evaluator: FormulaEvaluator | None = None) -> None:
        self._evaluator = evaluator or FormulaEvaluator()

    def create(self, *, template: CharacterTemplate, request: CharacterCreationInput) -> CharacterCreationResult:
        values = dict(request.fields)
        audit: list[CharacterCreationAudit] = []
        for formula in template.formulas:
            result = self._evaluator.evaluate_formula(formula, values)
            values[result.target_id] = result.value
            audit.append(
                CharacterCreationAudit(
                    formula_id=result.formula_id,
                    target_id=result.target_id,
                    value=result.value,
                    dependencies=list(result.dependencies),
                )
            )
        resources = {key: value for key, value in values.items() if isinstance(value, int) and key in _RESOURCE_IDS}
        traits = {key: value for key, value in values.items() if key not in resources}
        return CharacterCreationResult(
            character=CharacterState(
                id=request.character_id,
                name=request.name,
                owner=request.owner,
                resources=resources,
                traits=traits,
                skills=request.skills,
                conditions=request.conditions,
            ),
            audit=audit,
        )


_RESOURCE_IDS = {"hp", "mp", "sanity", "luck"}
