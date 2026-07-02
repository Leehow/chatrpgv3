from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.source import SourceRef


class RuleAtom(BaseModel):
    id: str
    system_id: str
    name: str
    kind: str
    summary: str
    source_refs: list[SourceRef] = Field(default_factory=list)


class ProcedureSpec(BaseModel):
    id: str
    system_id: str
    name: str
    inputs: list[str] = Field(default_factory=list)
    phases: list[dict[str, object]] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class RulesetIR(BaseModel):
    system_id: str
    edition: str
    rule_atoms: list[RuleAtom] = Field(default_factory=list)
    procedures: list[ProcedureSpec] = Field(default_factory=list)
    tables: list[dict[str, object]] = Field(default_factory=list)
    character_schema: dict[str, object] = Field(default_factory=dict)
    source_refs: list[SourceRef] = Field(default_factory=list)
