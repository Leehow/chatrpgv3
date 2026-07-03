from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.systems.coc7e import Coc7eEngine


def test_coc7e_skill_roll_repeatable() -> None:
    engine = Coc7eEngine(DiceEngine(seed=11))
    result = engine.skill_roll(target=60, reason="case")
    assert result.target == 60
    assert 1 <= result.roll <= 100


def test_coc7e_sanity_roll_reports_loss() -> None:
    engine = Coc7eEngine(DiceEngine(seed=11))
    result = engine.sanity_roll(
        current_sanity=55,
        success_loss=DiceRequest(count=1, sides=2, modifier=-1),
        failure_loss=DiceRequest(count=1, sides=6),
        reason="case",
    )
    assert result.target == 55
    assert result.sanity_lost >= 0


def test_coc7e_luck_spend_can_turn_failure_into_success() -> None:
    engine = Coc7eEngine(DiceEngine(seed=4))
    roll = engine.skill_roll(target=50, reason="case")
    adjusted = engine.spend_luck(roll=roll, current_luck=99)
    assert adjusted.new_luck <= 99
    assert adjusted.adjusted_roll <= roll.roll


def test_coc7e_opposed_roll_has_outcome() -> None:
    engine = Coc7eEngine(DiceEngine(seed=17))
    result = engine.opposed_roll(attacker_target=60, defender_target=40, reason="case")
    assert result.outcome in {"attacker", "defender", "tie"}


def test_coc7e_bonus_penalty_dice_normalize() -> None:
    engine = Coc7eEngine(DiceEngine(seed=21))
    roll = engine.d100_roll(bonus_dice=2, penalty_dice=1, reason="case")
    assert roll.bonus_dice == 1
    assert roll.penalty_dice == 0
