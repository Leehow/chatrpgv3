from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.runtime.dice import DiceEngine, DiceRequest

CocSuccessLevel = Literal["critical", "extreme", "hard", "regular", "failure", "fumble"]


class CocSkillRollResult(BaseModel):
    roll: int = Field(ge=1, le=100)
    target: int = Field(ge=1, le=100)
    level: CocSuccessLevel
    can_push: bool
    can_spend_luck: bool


class Coc7eEngine:
    def __init__(self, dice: DiceEngine) -> None:
        self._dice = dice

    def skill_roll(self, *, target: int, reason: str) -> CocSkillRollResult:
        dice_result = self._dice.roll(DiceRequest(count=1, sides=100), reason=reason)
        roll = dice_result.total
        level = self._success_level(roll=roll, target=target)
        return CocSkillRollResult(
            roll=roll,
            target=target,
            level=level,
            can_push=level in {"failure", "fumble"},
            can_spend_luck=level in {"failure", "fumble"},
        )

    @staticmethod
    def _success_level(*, roll: int, target: int) -> CocSuccessLevel:
        if roll == 1:
            return "critical"
        if roll >= 96 and target < 50:
            return "fumble"
        if roll == 100:
            return "fumble"
        if roll <= target // 5:
            return "extreme"
        if roll <= target // 2:
            return "hard"
        if roll <= target:
            return "regular"
        return "failure"
