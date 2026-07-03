from chatrpg.ir.adventure import ContentUnit
from chatrpg.runtime.visibility import VisibilityEngine


def test_visibility_blocks_keeper_only_units() -> None:
    unit = ContentUnit(
        id="u1",
        adventure_id="adv",
        kind="scene",
        title="Scene",
        summary="Summary",
        visibility="keeper_only",
    )
    decision = VisibilityEngine().can_show_unit(unit, revealed_unit_ids=set())
    assert decision.visible is False


def test_visibility_allows_revealed_units() -> None:
    unit = ContentUnit(
        id="u1",
        adventure_id="adv",
        kind="scene",
        title="Scene",
        summary="Summary",
        visibility="player_visible_after_found",
    )
    decision = VisibilityEngine().can_show_unit(unit, revealed_unit_ids={"u1"})
    assert decision.visible is True
