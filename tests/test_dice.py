from chatrpg.runtime.dice import DiceEngine, DiceRequest


def test_dice_engine_repeatable() -> None:
    first = DiceEngine(seed=11).roll(DiceRequest(count=2, sides=6), reason="case")
    second = DiceEngine(seed=11).roll(DiceRequest(count=2, sides=6), reason="case")
    assert first.rolls == second.rolls
    assert first.total == second.total
