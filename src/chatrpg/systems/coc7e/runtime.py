from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.runtime.dice import DiceEngine, DiceRequest

CocSuccessLevel = Literal["critical", "extreme", "hard", "regular", "failure", "fumble"]
OpposedOutcome = Literal["attacker", "defender", "tie"]


class CocD100Roll(BaseModel):
    value: int = Field(ge=1, le=100)
    unit_die: int = Field(ge=0, le=9)
    tens_dice: list[int] = Field(default_factory=list)
    bonus_dice: int = Field(default=0, ge=0)
    penalty_dice: int = Field(default=0, ge=0)


class CocSkillRollResult(BaseModel):
    roll: int = Field(ge=1, le=100)
    target: int = Field(ge=1, le=100)
    level: CocSuccessLevel
    can_push: bool
    can_spend_luck: bool
    luck_to_regular_success: int | None = None


class CocOpposedResult(BaseModel):
    attacker: CocSkillRollResult
    defender: CocSkillRollResult
    outcome: OpposedOutcome


class CocLuckSpendResult(BaseModel):
    original_roll: int
    adjusted_roll: int
    luck_spent: int
    new_luck: int
    level: CocSuccessLevel


class CocSanityResult(BaseModel):
    roll: int = Field(ge=1, le=100)
    target: int = Field(ge=0, le=99)
    success: bool
    sanity_lost: int = Field(ge=0)
    involuntary_action: bool


class Coc7eEngine:
    def __init__(self, dice: DiceEngine) -> None:
        self._dice = dice

    def d100_roll(self, *, bonus_dice: int = 0, penalty_dice: int = 0, reason: str) -> CocD100Roll:
        if bonus_dice and penalty_dice:
            offset = bonus_dice - penalty_dice
            bonus_dice = max(offset, 0)
            penalty_dice = max(-offset, 0)
        unit_die = self._dice.integer(low=0, high=9, reason=f"{reason}: units")
        tens_dice = [self._dice.integer(low=0, high=9, reason=f"{reason}: tens")]
        extra_count = bonus_dice or penalty_dice
        for index in range(extra_count):
            tens_dice.append(self._dice.integer(low=0, high=9, reason=f"{reason}: extra tens {index}"))
        selected_tens = min(tens_dice) if bonus_dice else max(tens_dice)
        value = selected_tens * 10 + unit_die
        if value == 0:
            value = 100
        return CocD100Roll(
            value=value,
            unit_die=unit_die,
            tens_dice=tens_dice,
            bonus_dice=bonus_dice,
            penalty_dice=penalty_dice,
        )

    def skill_roll(
        self,
        *,
        target: int,
        reason: str,
        bonus_dice: int = 0,
        penalty_dice: int = 0,
        allow_luck: bool = True,
    ) -> CocSkillRollResult:
        roll = self.d100_roll(bonus_dice=bonus_dice, penalty_dice=penalty_dice, reason=reason).value
        level = self._success_level(roll=roll, target=target)
        luck_needed = roll - target if roll > target else None
        return CocSkillRollResult(
            roll=roll,
            target=target,
            level=level,
            can_push=level in {"failure", "fumble"},
            can_spend_luck=allow_luck and luck_needed is not None,
            luck_to_regular_success=luck_needed,
        )

    def pushed_roll(self, *, target: int, reason: str) -> CocSkillRollResult:
        return self.skill_roll(target=target, reason=reason, allow_luck=False)

    def spend_luck(self, *, roll: CocSkillRollResult, current_luck: int) -> CocLuckSpendResult:
        if roll.luck_to_regular_success is None:
            return CocLuckSpendResult(
                original_roll=roll.roll,
                adjusted_roll=roll.roll,
                luck_spent=0,
                new_luck=current_luck,
                level=roll.level,
            )
        spent = min(current_luck, roll.luck_to_regular_success)
        adjusted_roll = roll.roll - spent
        return CocLuckSpendResult(
            original_roll=roll.roll,
            adjusted_roll=adjusted_roll,
            luck_spent=spent,
            new_luck=current_luck - spent,
            level=self._success_level(roll=adjusted_roll, target=roll.target),
        )

    def opposed_roll(
        self,
        *,
        attacker_target: int,
        defender_target: int,
        reason: str,
    ) -> CocOpposedResult:
        attacker = self.skill_roll(target=attacker_target, reason=f"{reason}: attacker", allow_luck=False)
        defender = self.skill_roll(target=defender_target, reason=f"{reason}: defender", allow_luck=False)
        outcome = self._opposed_outcome(attacker=attacker, defender=defender)
        return CocOpposedResult(attacker=attacker, defender=defender, outcome=outcome)

    def sanity_roll(
        self,
        *,
        current_sanity: int,
        success_loss: DiceRequest,
        failure_loss: DiceRequest,
        reason: str,
    ) -> CocSanityResult:
        roll = self.d100_roll(reason=reason).value
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

    @classmethod
    def _opposed_outcome(
        cls,
        *,
        attacker: CocSkillRollResult,
        defender: CocSkillRollResult,
    ) -> OpposedOutcome:
        attacker_rank = cls._level_rank(attacker.level)
        defender_rank = cls._level_rank(defender.level)
        if attacker_rank > defender_rank:
            return "attacker"
        if defender_rank > attacker_rank:
            return "defender"
        if attacker.roll < defender.roll:
            return "attacker"
        if defender.roll < attacker.roll:
            return "defender"
        return "tie"

    @staticmethod
    def _level_rank(level: CocSuccessLevel) -> int:
        rank_by_level = {
            "fumble": 0,
            "failure": 1,
            "regular": 2,
            "hard": 3,
            "extreme": 4,
            "critical": 5,
        }
        return rank_by_level[level]

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
