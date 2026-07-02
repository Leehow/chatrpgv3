from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.ir.source import SourceRef

PhaseKind = Literal[
    "session_setup",
    "character_creation",
    "briefing",
    "free_play",
    "procedure",
    "encounter",
    "combat",
    "downtime",
    "rest",
    "advancement",
    "debrief",
    "custom",
]
TransitionGuard = Literal["always", "party_exists", "manual"]


class WorkflowPhaseSpec(BaseModel):
    id: str
    label: str
    kind: PhaseKind
    description: str
    allows_adventure: bool = False
    allows_player_action: bool = True
    source_refs: list[SourceRef] = Field(default_factory=list)


class WorkflowTransitionSpec(BaseModel):
    id: str
    from_phase_id: str
    to_phase_id: str
    guard: TransitionGuard = "manual"
    automatic: bool = False
    description: str = ""
    source_refs: list[SourceRef] = Field(default_factory=list)


class WorkflowSpec(BaseModel):
    id: str
    system_id: str
    label: str
    initial_phase_id: str
    phases: list[WorkflowPhaseSpec] = Field(default_factory=list)
    transitions: list[WorkflowTransitionSpec] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)

    def phase_by_id(self, phase_id: str) -> WorkflowPhaseSpec | None:
        for phase in self.phases:
            if phase.id == phase_id:
                return phase
        return None

    def outgoing(self, phase_id: str) -> list[WorkflowTransitionSpec]:
        return [transition for transition in self.transitions if transition.from_phase_id == phase_id]
