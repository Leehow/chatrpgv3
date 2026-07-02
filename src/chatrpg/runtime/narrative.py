from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.runtime.progress import ProgressSnapshot

SceneFunction = Literal["orient", "investigate", "reveal", "threaten", "confront", "recover", "develop"]


class NarrativeBeatPlan(BaseModel):
    phase: str
    pressure: str
    recommended_functions: list[SceneFunction] = Field(default_factory=list)
    avoid_functions: list[SceneFunction] = Field(default_factory=list)
    required_event_types: list[str] = Field(default_factory=list)
    rationale: str


class NarrativeRuntime:
    def plan(self, *, progress: ProgressSnapshot) -> NarrativeBeatPlan:
        if progress.phase == "character_creation":
            return NarrativeBeatPlan(
                phase=progress.phase,
                pressure=progress.pressure,
                recommended_functions=["orient"],
                avoid_functions=["reveal", "confront"],
                required_event_types=["CharacterCreated"],
                rationale="No player character exists, so the next beat must complete investigator setup before adventure play.",
            )
        if progress.phase == "opening":
            return NarrativeBeatPlan(
                phase=progress.phase,
                pressure=progress.pressure,
                recommended_functions=["orient", "investigate"],
                avoid_functions=["confront"],
                required_event_types=["FrontierUnlocked", "ClueDiscovered"],
                rationale="The case has started but no revelations are confirmed, so orient the players and present actionable investigation paths.",
            )
        if progress.phase == "climax":
            return NarrativeBeatPlan(
                phase=progress.phase,
                pressure=progress.pressure,
                recommended_functions=["threaten", "confront", "reveal"],
                avoid_functions=["orient"],
                required_event_types=["ProcedureCompleted", "AttackResolved", "SanityRollResolved"],
                rationale="Most core revelations are known; escalate pressure and move toward confrontation or decisive revelation.",
            )
        if progress.phase == "development":
            return NarrativeBeatPlan(
                phase=progress.phase,
                pressure=progress.pressure,
                recommended_functions=["recover", "develop"],
                avoid_functions=["threaten", "confront"],
                required_event_types=["SkillImprovementResolved", "CharacterResourceChanged"],
                rationale="The adventure is in development or downtime, so resolve recovery, learning, and between-case changes.",
            )
        return NarrativeBeatPlan(
            phase=progress.phase,
            pressure=progress.pressure,
            recommended_functions=["investigate", "reveal", "threaten"],
            avoid_functions=[],
            required_event_types=["ClueDiscovered", "FactLearned", "FrontierUnlocked"],
            rationale="The investigation is underway; alternate clue acquisition, partial revelation, and pressure beats.",
        )
