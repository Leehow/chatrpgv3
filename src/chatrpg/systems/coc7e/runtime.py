from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.runtime.resolution import D100RollTrace, DiceRollTrace, ResolutionTrace, RuleFormulaTrace

CocSuccessLevel = Literal["critical", "extreme", "hard", "regular", "failure", "fumble"]
CocDifficulty = Literal["regular", "hard", "extreme"]
OpposedOutcome = Literal["attacker", "defender", "tie"]


class CocD100Roll(BaseModel):
    value: int = Field(ge=1, le=100)
    unit_die: int = Field(ge=0, le=9)
    tens_dice: list[int] = Field(default_factory=list)
    selected_tens: int = Field(ge=0, le=9)
    bonus_dice: int = Field(default=0, ge=0)
    penalty_dice: int = Field(default=0, ge=0)
    reason: str = ""

    def trace(self) -> D100RollTrace:
        return D100RollTrace(
            value=self.value,
            unit_die=self.unit_die,
            tens_dice=self.tens_dice,
            selected_tens=self.selected_tens,
            bonus_dice=self.bonus_dice,
            penalty_dice=self.penalty_dice,
            reason=self.reason,
        )


class CocSkillRollResult(BaseModel):
    roll: int = Field(ge=1, le=100)
    target: int = Field(ge=1, le=100)
    difficulty: CocDifficulty = "regular"
    thresholds: dict[str, int] = Field(default_factory=dict)
    level: CocSuccessLevel
    passed: bool = False
    can_push: bool
    can_spend_luck: bool
    luck_to_success: int | None = None
    luck_to_regular_success: int | None = None
    d100: CocD100Roll | None = None
    resolution: ResolutionTrace | None = None


class CocOpposedResult(BaseModel):
    attacker: CocSkillRollResult
    defender: CocSkillRollResult
    outcome: OpposedOutcome
    resolution: ResolutionTrace | None = None


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
    sanity_after: int = Field(ge=0, le=99)
    involuntary_action: bool
    temporary_insanity: bool
    indefinite_insanity: bool = False
    d100: CocD100Roll | None = None
    loss_roll: DiceRollTrace | None = None
    resolution: ResolutionTrace | None = None


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
            selected_tens=selected_tens,
            bonus_dice=bonus_dice,
            penalty_dice=penalty_dice,
            reason=reason,
        )

    def skill_roll(
        self,
        *,
        target: int,
        reason: str,
        bonus_dice: int = 0,
        penalty_dice: int = 0,
        difficulty: CocDifficulty = "regular",
        allow_luck: bool = True,
    ) -> CocSkillRollResult:
        d100 = self.d100_roll(bonus_dice=bonus_dice, penalty_dice=penalty_dice, reason=reason)
        thresholds = self._thresholds(target)
        level = self._success_level(roll=d100.value, target=target)
        required_threshold = thresholds[difficulty]
        passed = self._level_rank(level) >= self._level_rank(difficulty)
        luck_needed = d100.value - required_threshold if d100.value > required_threshold else None
        regular_luck_needed = d100.value - target if d100.value > target else None
        resolution = ResolutionTrace(
            kind="coc7e.skill_roll",
            title=f"CoC 7e 检定：{reason}",
            rules=[
                RuleFormulaTrace(
                    rule_id="coc7e.success_thresholds",
                    label="成功等级阈值",
                    formula="regular=skill, hard=floor(skill/2), extreme=floor(skill/5); roll<=threshold succeeds at that level",
                    inputs={"skill": target, "difficulty": difficulty},
                    output=required_threshold,
                ),
                RuleFormulaTrace(
                    rule_id="coc7e.success_level",
                    label="成功等级判定",
                    formula="1=critical; <=floor(skill/5)=extreme; <=floor(skill/2)=hard; <=skill=regular; 96-100/100 may fumble",
                    inputs={"roll": d100.value, "skill": target},
                    output=level,
                ),
            ],
            dice=[d100.trace()],
            outcome={
                "passed": passed,
                "level": level,
                "difficulty": difficulty,
                "roll": d100.value,
                "target": target,
                "thresholds": thresholds,
                "luck_to_success": luck_needed,
                "can_push": not passed,
            },
        )
        return CocSkillRollResult(
            roll=d100.value,
            target=target,
            difficulty=difficulty,
            thresholds=thresholds,
            level=level,
            passed=passed,
            can_push=not passed,
            can_spend_luck=allow_luck and luck_needed is not None,
            luck_to_success=luck_needed,
            luck_to_regular_success=regular_luck_needed,
            d100=d100,
            resolution=resolution,
        )

    def pushed_roll(self, *, target: int, reason: str, difficulty: CocDifficulty = "regular") -> CocSkillRollResult:
        return self.skill_roll(target=target, reason=reason, difficulty=difficulty, allow_luck=False)

    def spend_luck(self, *, roll: CocSkillRollResult, current_luck: int) -> CocLuckSpendResult:
        needed = roll.luck_to_success if roll.luck_to_success is not None else roll.luck_to_regular_success
        if needed is None:
            return CocLuckSpendResult(
                original_roll=roll.roll,
                adjusted_roll=roll.roll,
                luck_spent=0,
                new_luck=current_luck,
                level=roll.level,
            )
        spent = min(current_luck, needed)
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
        return CocOpposedResult(
            attacker=attacker,
            defender=defender,
            outcome=outcome,
            resolution=ResolutionTrace(
                kind="coc7e.opposed_roll",
                title=f"CoC 7e 对抗检定：{reason}",
                rules=[
                    RuleFormulaTrace(
                        rule_id="coc7e.opposed_roll",
                        label="对抗检定",
                        formula="Both sides roll 1D100; compare success level first, then lower roll breaks tied success levels.",
                        inputs={"attacker_target": attacker_target, "defender_target": defender_target},
                        output=outcome,
                    )
                ],
                dice=[attacker.d100.trace(), defender.d100.trace()] if attacker.d100 and defender.d100 else [],
                outcome={"winner": outcome, "attacker_level": attacker.level, "defender_level": defender.level},
            ),
        )

    def sanity_roll(
        self,
        *,
        current_sanity: int,
        success_loss: DiceRequest,
        failure_loss: DiceRequest,
        reason: str,
        starting_sanity_for_day: int | None = None,
    ) -> CocSanityResult:
        d100 = self.d100_roll(reason=reason)
        success = d100.value <= current_sanity
        loss_request = success_loss if success else failure_loss
        loss_result = self._dice.roll(loss_request, reason=f"{reason}: loss")
        sanity_lost = max(0, loss_result.total)
        sanity_after = max(0, current_sanity - sanity_lost)
        temporary_insanity = sanity_lost >= 5
        baseline = current_sanity if starting_sanity_for_day is None else starting_sanity_for_day
        indefinite_insanity = baseline - sanity_after >= max(1, baseline // 5)
        resolution = ResolutionTrace(
            kind="coc7e.sanity_roll",
            title=f"CoC 7e 理智检定：{reason}",
            rules=[
                RuleFormulaTrace(
                    rule_id="coc7e.sanity_roll",
                    label="SAN 检定",
                    formula="roll 1D100 <= current SAN succeeds; success uses success_loss, failure uses failure_loss",
                    inputs={"roll": d100.value, "current_sanity": current_sanity},
                    output=success,
                ),
                RuleFormulaTrace(
                    rule_id="coc7e.temporary_insanity",
                    label="临时疯狂阈值",
                    formula="single SAN loss >= 5 triggers involuntary action / possible temporary insanity handling",
                    inputs={"sanity_lost": sanity_lost},
                    output=temporary_insanity,
                ),
                RuleFormulaTrace(
                    rule_id="coc7e.indefinite_insanity",
                    label="不定性疯狂阈值",
                    formula="daily SAN loss >= one fifth of starting SAN for the day",
                    inputs={"starting_sanity_for_day": baseline, "sanity_after": sanity_after},
                    output=indefinite_insanity,
                ),
            ],
            dice=[d100.trace(), DiceRollTrace.from_result(loss_result)],
            outcome={
                "success": success,
                "sanity_lost": sanity_lost,
                "sanity_after": sanity_after,
                "temporary_insanity": temporary_insanity,
                "indefinite_insanity": indefinite_insanity,
            },
        )
        return CocSanityResult(
            roll=d100.value,
            target=current_sanity,
            success=success,
            sanity_lost=sanity_lost,
            sanity_after=sanity_after,
            involuntary_action=temporary_insanity,
            temporary_insanity=temporary_insanity,
            indefinite_insanity=indefinite_insanity,
            d100=d100,
            loss_roll=DiceRollTrace.from_result(loss_result),
            resolution=resolution,
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
    def _level_rank(level: str) -> int:
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
    def _thresholds(target: int) -> dict[str, int]:
        return {"regular": target, "hard": target // 2, "extreme": target // 5}

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
