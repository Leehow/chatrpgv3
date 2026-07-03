from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.ir.source import SourceRef

FieldKind = Literal["characteristic", "derived", "resource", "skill", "background", "choice"]
FormulaKind = Literal["arithmetic", "banded"]


class CharacterFieldSpec(BaseModel):
    id: str
    label: str
    kind: FieldKind
    default: int | str | None = None
    minimum: int | None = None
    maximum: int | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class FormulaBand(BaseModel):
    upper: int
    value: int | str


class FormulaSpec(BaseModel):
    id: str
    target_id: str
    kind: FormulaKind = "arithmetic"
    expression: str | None = None
    bands: list[FormulaBand] = Field(default_factory=list)
    default: int | str | None = None
    depends_on: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class CreationStepSpec(BaseModel):
    id: str
    label: str
    description: str
    required_fields: list[str] = Field(default_factory=list)
    formulas_to_apply: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class CharacterTemplate(BaseModel):
    id: str
    system_id: str
    label: str
    fields: list[CharacterFieldSpec] = Field(default_factory=list)
    formulas: list[FormulaSpec] = Field(default_factory=list)
    creation_steps: list[CreationStepSpec] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)

    def formula_by_id(self, formula_id: str) -> FormulaSpec | None:
        for formula in self.formulas:
            if formula.id == formula_id:
                return formula
        return None
