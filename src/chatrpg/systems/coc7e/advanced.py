from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.runtime.resolution import DiceRollTrace, ResolutionTrace, RuleFormulaTrace
from chatrpg.systems.coc7e.runtime import Coc7eEngine, CocSkillRollResult

CombatRange = Literal["melee", "firearm", "thrown"]
ChaseRole = Literal["pursuer", "quarry"]
MagicOutcome = Literal["cast", "insufficient_resources", "failed_roll"]
DamageSeverity = Literal["none", "minor", "major", "dead"]


class CocDamageResult(BaseModel):
    rolled_damage: int = Field(ge=0)
    impale_bonus: int = Field(default=0, ge=0)
    total_damage: int = Field(ge=0)
    damage_roll: DiceRollTrace | None = None
    resolution: ResolutionTrace | None = None


class CocAttackResult(BaseModel):
    attack_roll: CocSkillRollResult
    range_type: CombatRange
    hit: bool
    damage: CocDamageResult | None = None
    resolution: ResolutionTrace | None = None


class CocCombatSettlement(BaseModel):
    attack: CocAttackResult
    target_hp_before: int = Field(ge=0)
    target_hp_after: int = Field(ge=0)
    armor: int = Field(default=0, ge=0)
    applied_damage: int = Field(default=0, ge=0)
    severity: DamageSeverity
    major_wound: bool
    dead: bool
    resolution: ResolutionTrace


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
        impale: bool = True,
    ) -> CocAttackResult:
        attack_roll = self._coc.skill_roll(
            target=target,
            reason=reason,
            bonus_dice=bonus_dice,
            penalty_dice=penalty_dice,
        )
        hit = attack_roll.passed
        damage_result = None
        damage_trace = None
        if hit:
            rolled_result = self._dice.roll(damage, reason=f"{reason}: damage")
            damage_trace = DiceRollTrace.from_result(rolled_result)
            impale_bonus = damage.sides if impale and attack_roll.level in {"extreme", "critical"} else 0
            damage_result = CocDamageResult(
                rolled_damage=rolled_result.total,
                impale_bonus=impale_bonus,
                total_damage=rolled_result.total + impale_bonus,
                damage_roll=damage_trace,
                resolution=ResolutionTrace(
                    kind="coc7e.damage_roll",
                    title=f"CoC 7e 伤害掷骰：{reason}",
                    rules=[
                        RuleFormulaTrace(
                            rule_id="coc7e.damage_total",
                            label="伤害总计",
                            formula="rolled_damage + impale_bonus",
                            inputs={"rolled_damage": rolled_result.total, "impale_bonus": impale_bonus},
                            output=rolled_result.total + impale_bonus,
                        )
                    ],
                    dice=[damage_trace],
                    outcome={"total_damage": rolled_result.total + impale_bonus},
                ),
            )
        resolution = ResolutionTrace(
            kind="coc7e.combat_attack",
            title=f"CoC 7e 攻击检定：{reason}",
            rules=[
                RuleFormulaTrace(
                    rule_id="coc7e.attack_hit",
                    label="命中判定",
                    formula="attack skill roll passes required difficulty; failed/fumbled rolls miss",
                    inputs={"target": target, "roll": attack_roll.roll, "level": attack_roll.level},
                    output=hit,
                )
            ],
            dice=[attack_roll.d100.trace()] if attack_roll.d100 else [],
            outcome={
                "hit": hit,
                "range_type": range_type,
                "damage": None if damage_result is None else damage_result.total_damage,
            },
        )
        return CocAttackResult(
            attack_roll=attack_roll,
            range_type=range_type,
            hit=hit,
            damage=damage_result,
            resolution=resolution,
        )

    def settle_attack(
        self,
        *,
        target: int,
        damage: DiceRequest,
        target_hp: int,
        reason: str,
        armor: int = 0,
        range_type: CombatRange = "melee",
        bonus_dice: int = 0,
        penalty_dice: int = 0,
    ) -> CocCombatSettlement:
        attack = self.attack(
            target=target,
            damage=damage,
            reason=reason,
            range_type=range_type,
            bonus_dice=bonus_dice,
            penalty_dice=penalty_dice,
        )
        total_damage = 0 if attack.damage is None else attack.damage.total_damage
        applied_damage = max(0, total_damage - armor)
        hp_after = max(0, target_hp - applied_damage)
        major_wound = applied_damage >= max(1, target_hp // 2)
        if hp_after == 0:
            severity: DamageSeverity = "dead"
        elif major_wound:
            severity = "major"
        elif applied_damage > 0:
            severity = "minor"
        else:
            severity = "none"
        resolution = ResolutionTrace(
            kind="coc7e.combat_settlement",
            title=f"CoC 7e 战斗结算：{reason}",
            rules=[
                RuleFormulaTrace(
                    rule_id="coc7e.applied_damage",
                    label="护甲后伤害",
                    formula="max(0, total_damage - armor)",
                    inputs={"total_damage": total_damage, "armor": armor},
                    output=applied_damage,
                ),
                RuleFormulaTrace(
                    rule_id="coc7e.major_wound",
                    label="重伤判定",
                    formula="applied_damage >= floor(hp_before / 2)",
                    inputs={"applied_damage": applied_damage, "hp_before": target_hp},
                    output=major_wound,
                ),
            ],
            dice=[attack.attack_roll.d100.trace()] if attack.attack_roll.d100 else [],
            outcome={
                "hp_before": target_hp,
                "hp_after": hp_after,
                "applied_damage": applied_damage,
                "severity": severity,
                "major_wound": major_wound,
                "dead": hp_after == 0,
            },
        )
        if attack.damage and attack.damage.damage_roll:
            resolution.dice.append(attack.damage.damage_roll)
        return CocCombatSettlement(
            attack=attack,
            target_hp_before=target_hp,
            target_hp_after=hp_after,
            armor=armor,
            applied_damage=applied_damage,
            severity=severity,
            major_wound=major_wound,
            dead=hp_after == 0,
            resolution=resolution,
        )


class ChaseParticipant(BaseModel):
    id: str
    role: ChaseRole
    move: int
    dex: int = 0


class ChaseCheckResult(BaseModel):
    participant_id: str
    roll: CocSkillRollResult
    location_delta: int
    resolution: ResolutionTrace


class ChaseRound(BaseModel):
    order: list[str]
    gap_changes: dict[str, int] = Field(default_factory=dict)
    checks: list[ChaseCheckResult] = Field(default_factory=list)
    resolution: ResolutionTrace | None = None


class CocChaseEngine:
    def order_participants(self, participants: list[ChaseParticipant]) -> ChaseRound:
        ordered = sorted(participants, key=lambda item: (item.move, item.dex, item.id), reverse=True)
        return ChaseRound(
            order=[item.id for item in ordered],
            resolution=ResolutionTrace(
                kind="coc7e.chase_order",
                title="CoC 7e 追逐顺序",
                rules=[
                    RuleFormulaTrace(
                        rule_id="coc7e.chase_order",
                        label="追逐行动顺序",
                        formula="order by MOV, then DEX, then stable participant id",
                        inputs={participant.id: f"MOV {participant.move}, DEX {participant.dex}" for participant in participants},
                        output=", ".join(item.id for item in ordered),
                    )
                ],
                outcome={"order": [item.id for item in ordered]},
            ),
        )

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
        resolution = ResolutionTrace(
            kind="coc7e.chase_movement_check",
            title=f"CoC 7e 追逐移动检定：{participant_id}",
            rules=[
                RuleFormulaTrace(
                    rule_id="coc7e.chase_location_delta",
                    label="追逐位置变化",
                    formula="failure/fumble=-1, regular/hard=+1, extreme/critical=+2",
                    inputs={"level": result.level, "roll": result.roll, "target": target},
                    output=change,
                )
            ],
            dice=[result.d100.trace()] if result.d100 else [],
            outcome={"participant_id": participant_id, "location_delta": change},
        )
        check = ChaseCheckResult(participant_id=participant_id, roll=result, location_delta=change, resolution=resolution)
        return ChaseRound(order=[participant_id], gap_changes={participant_id: change}, checks=[check], resolution=resolution)


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
            if not roll.passed:
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
