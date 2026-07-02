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
