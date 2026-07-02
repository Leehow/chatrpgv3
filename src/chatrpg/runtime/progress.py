from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.state import SessionState

ProgressPhase = Literal["character_creation", "opening", "investigation", "climax", "development"]
PressureLevel = Literal["low", "medium", "high"]


class ProgressSnapshot(BaseModel):
    phase: ProgressPhase
    pressure: PressureLevel
    unlocked_unit_ids: list[str] = Field(default_factory=list)
    discovered_clue_ids: list[str] = Field(default_factory=list)
    known_revelation_ids: list[str] = Field(default_factory=list)
    unresolved_revelation_ids: list[str] = Field(default_factory=list)
    revealed_handout_ids: list[str] = Field(default_factory=list)
    completion_ratio: float = Field(ge=0.0, le=1.0)


class ProgressController:
    def snapshot(self, *, state: SessionState, adventure: AdventureIR | None = None) -> ProgressSnapshot:
        known_ids = [fact.id for fact in state.known_facts]
        unresolved_ids: list[str] = []
        completion_ratio = 0.0
        if adventure is not None and adventure.revelations:
            known_set = set(known_ids)
            unresolved_ids = [item.id for item in adventure.revelations if item.id not in known_set]
            completion_ratio = len(known_set.intersection({item.id for item in adventure.revelations})) / len(adventure.revelations)
        phase = self._phase(state=state, completion_ratio=completion_ratio)
        return ProgressSnapshot(
            phase=phase,
            pressure=self._pressure(state=state, completion_ratio=completion_ratio),
            unlocked_unit_ids=list(state.unlocked_frontier),
            discovered_clue_ids=list(state.discovered_clues),
            known_revelation_ids=known_ids,
            unresolved_revelation_ids=unresolved_ids,
            revealed_handout_ids=list(state.revealed_handouts),
            completion_ratio=completion_ratio,
        )

    @staticmethod
    def _phase(*, state: SessionState, completion_ratio: float) -> ProgressPhase:
        if not state.party:
            return "character_creation"
        if state.workflow_phase == "coc7e.development":
            return "development"
        if completion_ratio == 0.0:
            return "opening"
        if completion_ratio >= 0.75:
            return "climax"
        return "investigation"

    @staticmethod
    def _pressure(*, state: SessionState, completion_ratio: float) -> PressureLevel:
        if any(condition in {"dead", "dying", "major_wound", "temporary_insanity", "indefinite_insanity"} for character in state.party for condition in character.conditions):
            return "high"
        if completion_ratio >= 0.5 or state.active_procedures:
            return "medium"
        return "low"
