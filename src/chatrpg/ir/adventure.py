from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.source import SourceRef


class ContentUnit(BaseModel):
    id: str
    adventure_id: str
    kind: str
    title: str
    summary: str
    visibility: str
    parent_id: str | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class Revelation(BaseModel):
    id: str
    adventure_id: str
    truth_summary: str
    required_for: list[str] = Field(default_factory=list)
    unlocks: list[str] = Field(default_factory=list)
    redundancy_level: int = Field(default=1, ge=1)
    source_refs: list[SourceRef] = Field(default_factory=list)


class ClueCarrier(BaseModel):
    id: str
    revelation_id: str
    carrier_type: str
    unit_id: str
    acquisition: str
    fail_forward: str | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)


class AdventureIR(BaseModel):
    adventure_id: str
    system_id: str
    title: str
    units: list[ContentUnit] = Field(default_factory=list)
    revelations: list[Revelation] = Field(default_factory=list)
    clues: list[ClueCarrier] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
