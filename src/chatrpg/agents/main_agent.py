from __future__ import annotations

from chatrpg.agents.contracts import IntentFrame, NarrationRequest, NarrationResult, PlayerInput
from chatrpg.agents.pi_client import PiClient, PiMessage


class PiMainAgent:
    def __init__(self, client: PiClient) -> None:
        self._client = client

    async def resolve_intent(self, player_input: PlayerInput, *, trace_id: str) -> IntentFrame:
        messages = [
            PiMessage(
                role="system",
                content=(
                    "You are the intent interpreter for a source-grounded TRPG runtime. "
                    "You do not change state, roll dice, or reveal keeper-only information. "
                    "Return only schema-valid JSON."
                ),
            ),
            PiMessage(role="user", content=player_input.model_dump_json()),
        ]
        raw = await self._client.complete_json(
            task="main_agent.resolve_intent",
            messages=messages,
            json_schema=IntentFrame.model_json_schema(),
            trace_id=trace_id,
        )
        return IntentFrame.model_validate(raw)

    async def narrate(self, request: NarrationRequest, *, trace_id: str) -> NarrationResult:
        messages = [
            PiMessage(
                role="system",
                content=(
                    "You are the narrator for a TRPG session. Use only visible facts and committed events. "
                    "Do not reveal hidden, future, keeper-only, or runtime-only information. "
                    "Return only schema-valid JSON."
                ),
            ),
            PiMessage(role="user", content=request.model_dump_json()),
        ]
        raw = await self._client.complete_json(
            task="main_agent.narrate",
            messages=messages,
            json_schema=NarrationResult.model_json_schema(),
            trace_id=trace_id,
        )
        return NarrationResult.model_validate(raw)
