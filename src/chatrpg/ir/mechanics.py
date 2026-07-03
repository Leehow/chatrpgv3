from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from chatrpg.ir.source import SourceRef

MechanicTriggerKind = Literal[
    "aggression",
    "horror_exposure",
    "hazard_contact",
    "trap_activation",
    "ambush",
    "social_conflict",
    "chase_trigger",
    "spell_or_ritual",
    "tome_study",
    "environmental_damage",
    "custom",
]
MechanicVisibility = Literal["player_visible", "keeper_only", "runtime_only"]
MechanicPlanStatus = Literal["planned", "no_trigger", "ambiguous", "invalid"]
AssetResolutionPolicy = Literal["explicit", "derive", "template", "synthesize", "ask_clarification"]


class EntityRef(BaseModel):
    kind: str
    id: str
    label: str | None = None


class EntityMention(BaseModel):
    text: str
    ref: EntityRef | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ActionFrame(BaseModel):
    actor_id: str | None = None
    raw_text: str
    intent: str
    action_type: str = "other"
    targets: list[EntityMention] = Field(default_factory=list)
    instruments: list[EntityMention] = Field(default_factory=list)
    stated_goal: str | None = None
    force_level: str = "unclear"
    stealth_or_surprise: str = "unknown"
    ambiguity: list[str] = Field(default_factory=list)


class ActorPresence(BaseModel):
    ref: EntityRef
    name: str
    role: str | None = None
    visibility: MechanicVisibility = "player_visible"
    runtime_actor_id: str | None = None
    summary: str | None = None


class ObjectPresence(BaseModel):
    ref: EntityRef
    name: str
    visibility: MechanicVisibility = "player_visible"
    summary: str | None = None


class MechanicAffordance(BaseModel):
    id: str
    trigger_kind: MechanicTriggerKind
    trigger_description: str
    subject_ref: EntityRef | None = None
    procedure_candidates: list[str] = Field(default_factory=list)
    default_inputs: dict[str, Any] = Field(default_factory=dict)
    parameter_requirements: list[str] = Field(default_factory=list)
    visibility: MechanicVisibility = "keeper_only"
    priority: int = 0
    repeat_policy: str = "always"
    source_refs: list[SourceRef] = Field(default_factory=list)


class SceneFrame(BaseModel):
    scene_id: str
    location_id: str | None = None
    active_unit_ids: list[str] = Field(default_factory=list)
    present_actors: list[ActorPresence] = Field(default_factory=list)
    visible_objects: list[ObjectPresence] = Field(default_factory=list)
    active_affordances: list[MechanicAffordance] = Field(default_factory=list)
    recent_event_types: list[str] = Field(default_factory=list)


class MechanicStep(BaseModel):
    procedure_id: str
    actor_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class AssetRequirement(BaseModel):
    kind: str
    entity_ref: EntityRef | None = None
    resolution_policy: AssetResolutionPolicy = "explicit"
    reason: str | None = None


class TriggeredAffordance(BaseModel):
    affordance_id: str
    trigger_kind: MechanicTriggerKind
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    source_refs: list[SourceRef] = Field(default_factory=list)


class MechanicPlan(BaseModel):
    status: MechanicPlanStatus
    reason: str
    triggers: list[TriggeredAffordance] = Field(default_factory=list)
    ordered_steps: list[MechanicStep] = Field(default_factory=list)
    required_assets: list[AssetRequirement] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty: list[str] = Field(default_factory=list)


class ResolvedMechanicPlan(BaseModel):
    plan: MechanicPlan
    pre_events: list[Any] = Field(default_factory=list)
    steps: list[MechanicStep] = Field(default_factory=list)
