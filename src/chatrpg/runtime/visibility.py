from __future__ import annotations

from dataclasses import dataclass

from chatrpg.ir.adventure import ClueCarrier, ContentUnit, HandoutAsset


@dataclass(frozen=True)
class VisibilityDecision:
    visible: bool
    reason: str


class VisibilityEngine:
    def can_show_unit(self, unit: ContentUnit, *, revealed_unit_ids: set[str]) -> VisibilityDecision:
        if unit.visibility == "player_visible":
            return VisibilityDecision(visible=True, reason="unit is player-visible")
        if unit.visibility == "player_visible_after_found" and unit.id in revealed_unit_ids:
            return VisibilityDecision(visible=True, reason="unit was revealed")
        return VisibilityDecision(visible=False, reason="unit is not visible to players")

    def can_show_clue(self, clue: ClueCarrier, *, revealed_revelation_ids: set[str]) -> VisibilityDecision:
        if clue.visibility == "player_visible" or clue.revelation_id in revealed_revelation_ids:
            return VisibilityDecision(visible=True, reason="clue is available")
        return VisibilityDecision(visible=False, reason="clue is still keeper-only")

    def can_show_handout(self, handout: HandoutAsset, *, revealed_handout_ids: set[str]) -> VisibilityDecision:
        return VisibilityDecision(
            visible=handout.id in revealed_handout_ids,
            reason="handout reveal gate evaluated",
        )
