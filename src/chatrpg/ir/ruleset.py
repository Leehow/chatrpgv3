from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.source import SourceRef


class RuleAtom(BaseModel):
    id: str
    system_id: str
    name: str
    kind: str
    summary: str
    applies_to: list[str] = Field(default_factory=list)
    priority: int = 100
    source_refs: list[SourceRef] = Field(default_factory=list)


class RollSpec(BaseModel):
    id: str
    kernel_id: str
    inputs: list[str] = Field(default_factory=list)
    output: str | None = None


class ResourceChangeSpec(BaseModel):
    resource_id: str
    expression: str
    timing: str


class ProcedureSpec(BaseModel):
    id: str
    system_id: str
    name: str
    trigger: dict[str, object] = Field(default_factory=dict)
    inputs: list[str] = Field(default_factory=list)
    rolls: list[RollSpec] = Field(default_factory=list)
    phases: list[dict[str, object]] = Field(default_factory=list)
    resource_changes: list[ResourceChangeSpec] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class RuleTable(BaseModel):
    id: str
    system_id: str
    name: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, object]] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class RuleEntity(BaseModel):
    id: str
    system_id: str
    kind: str
    name: str
    payload: dict[str, object] = Field(default_factory=dict)
    source_refs: list[SourceRef] = Field(default_factory=list)


class RulesetIR(BaseModel):
    system_id: str
    edition: str
    rule_atoms: list[RuleAtom] = Field(default_factory=list)
    procedures: list[ProcedureSpec] = Field(default_factory=list)
    tables: list[RuleTable] = Field(default_factory=list)
    entities: list[RuleEntity] = Field(default_factory=list)
    character_schema: dict[str, object] = Field(default_factory=dict)
    resolution_kernels: list[dict[str, object]] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
