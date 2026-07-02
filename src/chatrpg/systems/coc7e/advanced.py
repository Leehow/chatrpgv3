from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.systems.coc7e.runtime import Coc7eEngine, CocSkillRollResult

CombatRange = Literal["melee", "firearm", "thrown"]
ChaseRole = Literal["pursuer", "quarry"]
MagicOutcome = Literal["cast", "insufficient_resources", "failed_roll"]


class CocDamageResult(BaseModel):
    rolled_damage: int = Field(ge=0)
    impale_bonus: int = Field(default=0, ge=0)
    total_damage: int = Field(ge=0)


class CocAttackResult(BaseModel):
    attack_roll: CocSkillRollResult
    range_type: CombatRange
    hit: bool
    damage: CocDamageResult | None = None


class CocCombatEngine:
    def __init__(self, coc: Coc7eEngine, dice: DiceEngine) -> None:
        self._coc = coc
        self._dice = dice

    def attack(
        self,
        *,
        target: int,
        damage: DiceRequest,
        reason: str,
        range_type: CombatRange = "melee",
        bonus_dice: int = 0,
        penalty_dice: int = 0,
    ) -> CocAttackResult:
        attack_roll = self._coc.skill_roll(
            target=target,
            reason=reason,
            bonus_dice=bonus_dice,
            penalty_dice=penalty_dice,
        )
        hit = attack_roll.level not in {"failure", "fumble"}
        damage_result = None
        if hit:
            rolled = self._dice.roll(damage, reason=f"{reason}: damage").total
            impale_bonus = damage.sides if attack_roll.level in {"extreme", "critical"} else 0
            damage_result = CocDamageResult(
                rolled_damage=rolled,
                impale_bonus=impale_bonus,
                total_damage=rolled + impale_bonus,
            )
        return CocAttackResult(
            attack_roll=attack_roll,
            range_type=range_type,
            hit=hit,
            damage=damage_result,
        )


class ChaseParticipant(BaseModel):
    id: str
    role: ChaseRole
    move: int
    dex: int = 0


class ChaseRound(BaseModel):
    order: list[str]
    gap_changes: dict[str, int] = Field(default_factory=dict)


class CocChaseEngine:
    def order_participants(self, participants: list[ChaseParticipant]) -> ChaseRound:
        ordered = sorted(participants, key=lambda item: (item.move, item.dex, item.id), reverse=True)
        return ChaseRound(order=[item.id for item in ordered])

    def movement_check(
        self,
        *,
        coc: Coc7eEngine,
        participant_id: str,
        target: int,
        reason: str,
    ) -> ChaseRound:
        result = coc.skill_roll(target=target, reason=reason, allow_luck=False)
        if result.level in {"failure", "fumble"}:
            change = -1
        elif result.level in {"extreme", "critical"}:
            change = 2
        else:
            change = 1
        return ChaseRound(order=[participant_id], gap_changes={participant_id: change})


class SpellCastResult(BaseModel):
    outcome: MagicOutcome
    mp_spent: int = Field(ge=0)
    sanity_spent: int = Field(ge=0)
    roll: CocSkillRollResult | None = None


class TomeStudyResult(BaseModel):
    title: str
    weeks_required: int = Field(ge=0)
    mythos_gain: int = Field(ge=0)
    sanity_loss: int = Field(ge=0)


class CocMythosEngine:
    def __init__(self, coc: Coc7eEngine, dice: DiceEngine) -> None:
        self._coc = coc
        self._dice = dice

    def cast_spell(
        self,
        *,
        current_mp: int,
        mp_cost: int,
        sanity_cost: DiceRequest,
        reason: str,
        power_roll_target: int | None = None,
    ) -> SpellCastResult:
        if current_mp < mp_cost:
            return SpellCastResult(outcome="insufficient_resources", mp_spent=0, sanity_spent=0)
        sanity_spent = self._dice.roll(sanity_cost, reason=f"{reason}: sanity cost").total
        roll = None
        if power_roll_target is not None:
            roll = self._coc.skill_roll(target=power_roll_target, reason=f"{reason}: power roll", allow_luck=False)
            if roll.level in {"failure", "fumble"}:
                return SpellCastResult(
                    outcome="failed_roll",
                    mp_spent=mp_cost,
                    sanity_spent=sanity_spent,
                    roll=roll,
                )
        return SpellCastResult(outcome="cast", mp_spent=mp_cost, sanity_spent=sanity_spent, roll=roll)

    def study_tome(
        self,
        *,
        title: str,
        weeks_required: int,
        mythos_gain: int,
        sanity_loss: DiceRequest,
        reason: str,
    ) -> TomeStudyResult:
        loss = self._dice.roll(sanity_loss, reason=f"{reason}: tome sanity loss").total
        return TomeStudyResult(
            title=title,
            weeks_required=weeks_required,
            mythos_gain=mythos_gain,
            sanity_loss=loss,
        )


class SkillImprovementResult(BaseModel):
    skill_id: str
    improved: bool
    gain: int = Field(ge=0)
    new_value: int = Field(ge=0, le=100)


class CocDevelopmentEngine:
    def __init__(self, coc: Coc7eEngine, dice: DiceEngine) -> None:
        self._coc = coc
        self._dice = dice

    def improve_skill(self, *, skill_id: str, current_value: int, reason: str) -> SkillImprovementResult:
        roll = self._coc.d100_roll(reason=f"{reason}: improvement check").value
        improved = roll > current_value or roll > 95
        gain = self._dice.roll(DiceRequest(count=1, sides=10), reason=f"{reason}: improvement gain").total if improved else 0
        return SkillImprovementResult(
            skill_id=skill_id,
            improved=improved,
            gain=gain,
            new_value=min(100, current_value + gain),
        )
