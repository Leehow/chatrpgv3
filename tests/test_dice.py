from chatrpg.runtime.dice import DiceEngine, DiceRequest, parse_dice_notation


def test_dice_engine_repeatable() -> None:
    first = DiceEngine(seed=11).roll(DiceRequest(count=2, sides=6), reason="case")
    second = DiceEngine(seed=11).roll(DiceRequest(count=2, sides=6), reason="case")
    assert first.rolls == second.rolls
    assert first.total == second.total


def test_parse_dice_notation_accepts_standard_damage_expressions() -> None:
    assert parse_dice_notation("1D6") == DiceRequest(count=1, sides=6)
    assert parse_dice_notation("d8+2") == DiceRequest(count=1, sides=8, modifier=2)
    assert parse_dice_notation("2d4 - 1") == DiceRequest(count=2, sides=4, modifier=-1)
    assert parse_dice_notation("not dice") is None
