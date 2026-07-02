from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.runtime.dice import DiceEngine, DiceRequest

TriangleOutcome = Literal["success", "mixed", "trouble"]


class TriangleRollResult(BaseModel):
    rolls: list[int]
    threes: int = Field(ge=0)
    chaos_delta: int
    outcome: TriangleOutcome


class TriangleAgencyEngine:
    def __init__(self, dice: DiceEngine) -> None:
        self._dice = dice

    def field_roll(self, *, dice_count: int = 6, reason: str) -> TriangleRollResult:
        rolls = list(self._dice.roll(DiceRequest(count=dice_count, sides=4), reason=reason).rolls)
        threes = sum(1 for value in rolls if value == 3)
        if threes >= 2:
            outcome: TriangleOutcome = "success"
            chaos_delta = -1
        elif threes == 1:
            outcome = "mixed"
            chaos_delta = 0
        else:
            outcome = "trouble"
            chaos_delta = 1
        return TriangleRollResult(rolls=rolls, threes=threes, chaos_delta=chaos_delta, outcome=outcome)
