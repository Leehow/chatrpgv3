from chatrpg.ir.adventure import ClueCarrier
from chatrpg.retrieval.semantic import SemanticChoice, SemanticMatchRequest, SemanticMatchResult
from chatrpg.runtime.clues import ClueAcquisitionEngine


class FakeMatcher:
    async def match(self, request: SemanticMatchRequest, *, trace_id: str) -> SemanticMatchResult:
        return SemanticMatchResult(
            status="matched",
            choices=[
                SemanticChoice(
                    candidate_id=request.candidates[0].id,
                    confidence=0.91,
                    rationale="fake semantic match",
                )
            ],
        )


def test_clue_acquisition_uses_semantic_matcher() -> None:
    async def run_case() -> None:
        clue = ClueCarrier(
            id="c1",
            revelation_id="r1",
            carrier_type="location_search",
            unit_id="u1",
            acquisition="skill_roll",
        )
        decision = await ClueAcquisitionEngine(FakeMatcher()).select_clue(
            player_action="inspect the room",
            available_clues=[clue],
            trace_id="trc",
        )
        assert decision.clue == clue
        assert decision.confidence == 0.91

    import asyncio

    asyncio.run(run_case())
