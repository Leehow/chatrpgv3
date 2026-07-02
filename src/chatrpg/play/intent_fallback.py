from __future__ import annotations

from chatrpg.agents.contracts import IntentFrame
from chatrpg.ir.state import CharacterState, SessionState
from chatrpg.retrieval.semantic import SemanticCandidate, SemanticMatchRequest, SemanticMatcher


async def infer_coc7e_skill_intent(
    *,
    player_action: str,
    state: SessionState,
    actor_id: str | None,
    matcher: SemanticMatcher,
    trace_id: str,
) -> IntentFrame | None:
    if state.system_id != "coc7e":
        return None
    actor = _actor(state=state, actor_id=actor_id)
    if actor is None or not actor.skills:
        return None
    candidates = [
        SemanticCandidate(
            id=skill_id,
            label=skill_id,
            description=f"CoC 7e investigator skill at {value}%.",
            metadata={"value": value},
        )
        for skill_id, value in actor.skills.items()
        if isinstance(value, int) and value > 0
    ]
    if not candidates:
        return None
    result = await matcher.match(
        SemanticMatchRequest(
            task="coc7e.intent.skill_fallback",
            query=player_action,
            candidates=candidates,
            instructions=(
                "Select the investigator skill that best resolves the player's declared action. "
                "Return no_match if the action is pure narration, movement, conversation without uncertainty, "
                "or if no listed skill is appropriate."
            ),
            confidence_floor=0.75,
        ),
        trace_id=trace_id,
    )
    if result.status != "matched" or not result.choices:
        return None
    choice = result.choices[0]
    if choice.confidence < 0.75:
        return None
    return IntentFrame(
        intent="规则检定",
        procedure_id="coc7e.skill_roll",
        actor_id=actor.id,
        inputs={"skill_id": choice.candidate_id, "reason": player_action},
        confidence=choice.confidence,
    )


def _actor(*, state: SessionState, actor_id: str | None) -> CharacterState | None:
    if actor_id is None:
        return state.party[0] if state.party else None
    return next((character for character in state.party if character.id == actor_id), None)
