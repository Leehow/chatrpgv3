from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.ir.mechanics import MechanicAffordance
from chatrpg.ir.source import SourceRef

Visibility = Literal["player_visible", "player_visible_after_found", "keeper_only", "runtime_only"]


class ContentUnit(BaseModel):
    id: str
    adventure_id: str
    kind: str
    title: str
    summary: str
    visibility: Visibility
    parent_id: str | None = None
    facets: list[str] = Field(default_factory=list)
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
    suggested_skills: list[str] = Field(default_factory=list)
    fail_forward: str | None = None
    visibility: Visibility = "keeper_only"
    source_refs: list[SourceRef] = Field(default_factory=list)


class NPCAsset(BaseModel):
    id: str
    adventure_id: str
    name: str
    summary: str
    public_profile: str | None = None
    keeper_profile: str | None = None
    stats_ref: str | None = None
    unit_ids: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class LocationAsset(BaseModel):
    id: str
    adventure_id: str
    name: str
    summary: str
    parent_location_id: str | None = None
    unit_ids: list[str] = Field(default_factory=list)
    exits_to: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class EncounterAsset(BaseModel):
    id: str
    adventure_id: str
    name: str
    summary: str
    procedure_ids: list[str] = Field(default_factory=list)
    unit_ids: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class HandoutAsset(BaseModel):
    id: str
    adventure_id: str
    title: str
    summary: str
    asset_ref: str | None = None
    reveals: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class TimelineStep(BaseModel):
    id: str
    adventure_id: str
    label: str
    summary: str
    unlocks: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)


class AdventureIR(BaseModel):
    adventure_id: str
    system_id: str
    title: str
    units: list[ContentUnit] = Field(default_factory=list)
    revelations: list[Revelation] = Field(default_factory=list)
    clues: list[ClueCarrier] = Field(default_factory=list)
    npcs: list[NPCAsset] = Field(default_factory=list)
    locations: list[LocationAsset] = Field(default_factory=list)
    encounters: list[EncounterAsset] = Field(default_factory=list)
    handouts: list[HandoutAsset] = Field(default_factory=list)
    timelines: list[TimelineStep] = Field(default_factory=list)
    affordances: list[MechanicAffordance] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
