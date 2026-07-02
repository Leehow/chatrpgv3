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


class CocSanityResult(BaseModel):
    roll: int = Field(ge=1, le=100)
    target: int = Field(ge=0, le=99)
    success: bool
    sanity_lost: int = Field(ge=0)
    involuntary_action: bool


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

    def sanity_roll(
        self,
        *,
        current_sanity: int,
        success_loss: DiceRequest,
        failure_loss: DiceRequest,
        reason: str,
    ) -> CocSanityResult:
        roll = self._dice.roll(DiceRequest(count=1, sides=100), reason=reason).total
        success = roll <= current_sanity
        loss_request = success_loss if success else failure_loss
        sanity_lost = self._dice.roll(loss_request, reason=f"{reason}: loss").total
        return CocSanityResult(
            roll=roll,
            target=current_sanity,
            success=success,
            sanity_lost=sanity_lost,
            involuntary_action=sanity_lost >= 5,
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
