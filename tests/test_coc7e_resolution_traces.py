from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.systems.coc7e.advanced import CocChaseEngine, CocCombatEngine
from chatrpg.systems.coc7e.runtime import Coc7eEngine


def test_skill_roll_exposes_thresholds_dice_and_formula_trace() -> None:
    engine = Coc7eEngine(DiceEngine(seed=11))
    result = engine.skill_roll(target=60, difficulty="hard", reason="library research")
    assert result.thresholds == {"regular": 60, "hard": 30, "extreme": 12}
    assert result.d100 is not None
    assert result.resolution is not None
    assert result.resolution.kind == "coc7e.skill_roll"
    assert result.resolution.dice[0].notation == "1D100"
    assert result.resolution.outcome["difficulty"] == "hard"


def test_sanity_roll_exposes_loss_dice_and_settled_sanity() -> None:
    engine = Coc7eEngine(DiceEngine(seed=12))
    result = engine.sanity_roll(
        current_sanity=45,
        success_loss=DiceRequest(count=1, sides=2, modifier=-1),
        failure_loss=DiceRequest(count=1, sides=6),
        reason="seeing horror",
        starting_sanity_for_day=45,
    )
    assert result.loss_roll is not None
    assert result.sanity_after == 45 - result.sanity_lost
    assert result.resolution is not None
    assert result.resolution.kind == "coc7e.sanity_roll"


def test_combat_settlement_exposes_attack_damage_and_hp_result() -> None:
    dice = DiceEngine(seed=13)
    result = CocCombatEngine(Coc7eEngine(dice), dice).settle_attack(
        target=90,
        damage=DiceRequest(count=1, sides=6),
        target_hp=10,
        armor=1,
        reason="knife attack",
    )
    assert result.target_hp_after <= 10
    assert result.resolution.kind == "coc7e.combat_settlement"
    assert any(die.notation == "1D100" for die in result.resolution.dice)


def test_chase_movement_check_exposes_roll_and_delta_formula() -> None:
    dice = DiceEngine(seed=14)
    result = CocChaseEngine().movement_check(
        coc=Coc7eEngine(dice),
        participant_id="pc1",
        target=60,
        reason="sprint through alley",
    )
    assert result.checks[0].resolution.kind == "coc7e.chase_movement_check"
    assert result.gap_changes["pc1"] in {-1, 1, 2}
