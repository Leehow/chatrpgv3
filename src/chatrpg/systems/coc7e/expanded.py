from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.systems.coc7e.runtime import Coc7eEngine, CocSkillRollResult

DamageSeverity = Literal["none", "minor", "major", "dead"]
MeleeChoice = Literal["dodge", "fight_back"]
ObstacleOutcome = Literal["cleared", "delayed", "crash"]
ReadingMode = Literal["initial", "full"]


class DamageApplication(BaseModel):
    incoming_damage: int = Field(ge=0)
    armor: int = Field(ge=0)
    applied_damage: int = Field(ge=0)
    hp_after: int = Field(ge=0)
    severity: DamageSeverity


class MeleeExchangeResult(BaseModel):
    attacker_roll: CocSkillRollResult
    defender_roll: CocSkillRollResult
    defender_choice: MeleeChoice
    attacker_hits: bool
    defender_hits: bool


class HealingResult(BaseModel):
    hp_before: int = Field(ge=0)
    hp_after: int = Field(ge=0)
    healed: int = Field(ge=0)


class CocWoundEngine:
    def apply_damage(self, *, hp: int, damage: int, armor: int = 0) -> DamageApplication:
        applied = max(0, damage - armor)
        hp_after = max(0, hp - applied)
        if hp_after == 0:
            severity: DamageSeverity = "dead"
        elif applied >= max(1, hp // 2):
            severity = "major"
        elif applied > 0:
            severity = "minor"
        else:
            severity = "none"
        return DamageApplication(
            incoming_damage=damage,
            armor=armor,
            applied_damage=applied,
            hp_after=hp_after,
            severity=severity,
        )

    def heal(self, *, hp: int, maximum_hp: int, healing: DiceRequest, dice: DiceEngine, reason: str) -> HealingResult:
        amount = dice.roll(healing, reason=reason).total
        hp_after = min(maximum_hp, hp + amount)
        return HealingResult(hp_before=hp, hp_after=hp_after, healed=hp_after - hp)


class CocMeleeEngine:
    def __init__(self, coc: Coc7eEngine) -> None:
        self._coc = coc

    def exchange(
        self,
        *,
        attacker_target: int,
        defender_target: int,
        defender_choice: MeleeChoice,
        reason: str,
    ) -> MeleeExchangeResult:
        attacker = self._coc.skill_roll(target=attacker_target, reason=f"{reason}: attack", allow_luck=False)
        defender = self._coc.skill_roll(target=defender_target, reason=f"{reason}: defense", allow_luck=False)
        attacker_rank = self._rank(attacker.level)
        defender_rank = self._rank(defender.level)
        if defender_choice == "dodge":
            attacker_hits = attacker_rank > defender_rank and attacker_rank > 1
            defender_hits = False
        else:
            attacker_hits = attacker_rank >= defender_rank and attacker_rank > 1
            defender_hits = defender_rank > attacker_rank and defender_rank > 1
        return MeleeExchangeResult(
            attacker_roll=attacker,
            defender_roll=defender,
            defender_choice=defender_choice,
            attacker_hits=attacker_hits,
            defender_hits=defender_hits,
        )

    @staticmethod
    def _rank(level: str) -> int:
        return {"fumble": 0, "failure": 1, "regular": 2, "hard": 3, "extreme": 4, "critical": 5}[level]


class ChaseObstacle(BaseModel):
    id: str
    difficulty: int = Field(ge=1, le=100)
    damage: DiceRequest | None = None


class ChaseObstacleResult(BaseModel):
    obstacle_id: str
    roll: CocSkillRollResult
    outcome: ObstacleOutcome
    damage: int = Field(default=0, ge=0)


class CocChaseObstacleEngine:
    def __init__(self, coc: Coc7eEngine, dice: DiceEngine) -> None:
        self._coc = coc
        self._dice = dice

    def resolve(self, *, obstacle: ChaseObstacle, participant_id: str, reason: str) -> ChaseObstacleResult:
        roll = self._coc.skill_roll(target=obstacle.difficulty, reason=f"{reason}: {participant_id}", allow_luck=False)
        if roll.level in {"failure", "fumble"}:
            damage = 0 if obstacle.damage is None else self._dice.roll(obstacle.damage, reason=f"{reason}: impact").total
            return ChaseObstacleResult(obstacle_id=obstacle.id, roll=roll, outcome="crash", damage=damage)
        if roll.level == "regular":
            return ChaseObstacleResult(obstacle_id=obstacle.id, roll=roll, outcome="delayed")
        return ChaseObstacleResult(obstacle_id=obstacle.id, roll=roll, outcome="cleared")


class TomeReadingResult(BaseModel):
    title: str
    mode: ReadingMode
    weeks_spent: int = Field(ge=0)
    mythos_gain: int = Field(ge=0)
    spells_available: list[str] = Field(default_factory=list)
    sanity_loss: int = Field(ge=0)


class SpellLearningResult(BaseModel):
    spell_id: str
    learned: bool
    weeks_spent: int = Field(ge=0)


class CocTomeEngine:
    def __init__(self, dice: DiceEngine) -> None:
        self._dice = dice

    def read(
        self,
        *,
        title: str,
        mode: ReadingMode,
        weeks: int,
        mythos_gain: int,
        sanity_loss: DiceRequest,
        spells_available: list[str],
        reason: str,
    ) -> TomeReadingResult:
        loss = self._dice.roll(sanity_loss, reason=f"{reason}: sanity").total
        return TomeReadingResult(
            title=title,
            mode=mode,
            weeks_spent=weeks,
            mythos_gain=mythos_gain,
            spells_available=spells_available,
            sanity_loss=loss,
        )

    def learn_spell(self, *, spell_id: str, weeks: int) -> SpellLearningResult:
        return SpellLearningResult(spell_id=spell_id, learned=True, weeks_spent=weeks)
