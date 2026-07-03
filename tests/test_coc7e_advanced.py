from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.systems.coc7e import (
    ChaseParticipant,
    Coc7eEngine,
    CocChaseEngine,
    CocCombatEngine,
    CocDevelopmentEngine,
    CocMythosEngine,
)


def test_coc7e_combat_attack_resolves_hit_shape() -> None:
    dice = DiceEngine(seed=31)
    coc = Coc7eEngine(dice)
    result = CocCombatEngine(coc, dice).attack(
        target=90,
        damage=DiceRequest(count=1, sides=6),
        reason="case",
    )
    assert result.attack_roll.target == 90
    assert result.range_type == "melee"
    if result.hit:
        assert result.damage is not None


def test_coc7e_chase_orders_by_move_then_dex() -> None:
    result = CocChaseEngine().order_participants(
        [
            ChaseParticipant(id="slow", role="quarry", move=7, dex=80),
            ChaseParticipant(id="fast", role="pursuer", move=9, dex=20),
        ]
    )
    assert result.order[0] == "fast"


def test_coc7e_spell_cast_spends_resources() -> None:
    dice = DiceEngine(seed=42)
    coc = Coc7eEngine(dice)
    result = CocMythosEngine(coc, dice).cast_spell(
        current_mp=10,
        mp_cost=3,
        sanity_cost=DiceRequest(count=1, sides=2, modifier=-1),
        reason="case",
    )
    assert result.mp_spent == 3
    assert result.sanity_spent >= 0


def test_coc7e_tome_study_returns_gain_and_loss() -> None:
    dice = DiceEngine(seed=42)
    coc = Coc7eEngine(dice)
    result = CocMythosEngine(coc, dice).study_tome(
        title="Example Tome",
        weeks_required=4,
        mythos_gain=3,
        sanity_loss=DiceRequest(count=1, sides=4),
        reason="case",
    )
    assert result.mythos_gain == 3
    assert result.sanity_loss >= 1


def test_coc7e_development_caps_skill_value() -> None:
    dice = DiceEngine(seed=1)
    coc = Coc7eEngine(dice)
    result = CocDevelopmentEngine(coc, dice).improve_skill(
        skill_id="spot_hidden",
        current_value=99,
        reason="case",
    )
    assert result.new_value <= 100
