from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class KnownFact(BaseModel):
    id: str
    known_by: str
    confidence: Literal["confirmed", "rumor", "lie", "hallucination", "partial"]
    source_event_id: str


class CharacterState(BaseModel):
    id: str
    name: str
    owner: str | None = None
    resources: dict[str, int] = Field(default_factory=dict)
    traits: dict[str, object] = Field(default_factory=dict)
    skills: dict[str, int] = Field(default_factory=dict)
    conditions: list[str] = Field(default_factory=list)


class NPCState(BaseModel):
    id: str
    name: str
    disposition: str | None = None
    known_facts: list[str] = Field(default_factory=list)
    resources: dict[str, int] = Field(default_factory=dict)


class RuntimeItemState(BaseModel):
    id: str
    name: str
    kind: str
    owner_actor_id: str | None = None
    profile: dict[str, object] = Field(default_factory=dict)
    visibility: Literal["player_visible", "keeper_only", "runtime_only"] = "keeper_only"
    provenance: dict[str, object] = Field(default_factory=dict)


class SessionState(BaseModel):
    id: str
    system_id: str
    adventure_id: str | None = None
    workflow_phase: str | None = None
    completed_workflow_phases: list[str] = Field(default_factory=list)
    current_units: list[str] = Field(default_factory=list)
    party: list[CharacterState] = Field(default_factory=list)
    npcs: list[NPCState] = Field(default_factory=list)
    runtime_actors: list[CharacterState] = Field(default_factory=list)
    runtime_items: list[RuntimeItemState] = Field(default_factory=list)
    known_facts: list[KnownFact] = Field(default_factory=list)
    secrets: list[dict[str, object]] = Field(default_factory=list)
    active_procedures: list[dict[str, object]] = Field(default_factory=list)
    pending_decisions: list[dict[str, object]] = Field(default_factory=list)
    pending_clues: list[dict[str, object]] = Field(default_factory=list)
    unlocked_frontier: list[str] = Field(default_factory=list)
    revealed_handouts: list[str] = Field(default_factory=list)
    discovered_clues: list[str] = Field(default_factory=list)
