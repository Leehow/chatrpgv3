from chatrpg.runtime.dice import DiceEngine
from chatrpg.systems.coc7e import Coc7eEngine


def test_coc7e_skill_roll_repeatable() -> None:
    engine = Coc7eEngine(DiceEngine(seed=11))
    result = engine.skill_roll(target=60, reason="case")
    assert result.target == 60
    assert 1 <= result.roll <= 100
