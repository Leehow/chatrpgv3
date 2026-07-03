from __future__ import annotations

from dataclasses import dataclass

from chatrpg.ir.adventure import ClueCarrier
from chatrpg.retrieval.semantic import SemanticCandidate, SemanticMatchRequest, SemanticMatcher


@dataclass(frozen=True)
class ClueAcquisitionDecision:
    clue: ClueCarrier | None
    status: str
    confidence: float
    rationale: str


class ClueAcquisitionEngine:
    def __init__(self, matcher: SemanticMatcher) -> None:
        self._matcher = matcher

    async def select_clue(
        self,
        *,
        player_action: str,
        available_clues: list[ClueCarrier],
        trace_id: str,
    ) -> ClueAcquisitionDecision:
        if not available_clues:
            return ClueAcquisitionDecision(
                clue=None,
                status="no_match",
                confidence=0.0,
                rationale="No clue carriers are currently in the unlocked frontier.",
            )
        candidates = [
            SemanticCandidate(
                id=clue.id,
                label=clue.carrier_type,
                description=clue.fail_forward,
                metadata={
                    "revelation_id": clue.revelation_id,
                    "unit_id": clue.unit_id,
                    "acquisition": clue.acquisition,
                    "suggested_skills": clue.suggested_skills,
                },
            )
            for clue in available_clues
        ]
        result = await self._matcher.match(
            SemanticMatchRequest(
                task="adventure.clue_acquisition.select",
                query=player_action,
                candidates=candidates,
                instructions=(
                    "Select the clue carrier whose acquisition conditions best match the player action. "
                    "Use only semantic meaning, not literal keyword matching."
                ),
            ),
            trace_id=trace_id,
        )
        if not result.choices:
            return ClueAcquisitionDecision(
                clue=None,
                status=result.status,
                confidence=0.0,
                rationale="Semantic matcher did not select a clue carrier.",
            )
        choice = result.choices[0]
        selected = next((clue for clue in available_clues if clue.id == choice.candidate_id), None)
        return ClueAcquisitionDecision(
            clue=selected,
            status=result.status,
            confidence=choice.confidence,
            rationale=choice.rationale,
        )
