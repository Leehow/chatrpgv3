from __future__ import annotations

import orjson

from chatrpg.agents.pi_client import PiClient, PiMessage
from chatrpg.sim.models import CompletionAssessment, SimPlayerObservation, SimulatedPlayerAction


class SimulatedPlayerAgent:
    def __init__(self, client: PiClient) -> None:
        self._client = client

    async def choose_action(self, observation: SimPlayerObservation, *, trace_id: str) -> SimulatedPlayerAction:
        raw = await self._client.complete_json(
            task="simulated_player.choose_action",
            messages=[
                PiMessage(
                    role="system",
                    content=(
                        "You simulate one realistic human TRPG player. You only know the visible transcript. "
                        "Act with curiosity, caution, imperfect memory, social reasoning, and scenario goals. "
                        "Do not use hidden GM knowledge. Do not speedrun by guessing secrets. Choose one concise player action."
                    ),
                ),
                PiMessage(role="user", content=observation.model_dump_json()),
            ],
            json_schema=SimulatedPlayerAction.model_json_schema(),
            trace_id=trace_id,
        )
        return SimulatedPlayerAction.model_validate(raw)

    async def assess_completion(
        self,
        *,
        observation: SimPlayerObservation,
        last_action: SimulatedPlayerAction | None,
        turn_limit_reached: bool,
        trace_id: str,
    ) -> CompletionAssessment:
        if turn_limit_reached:
            return CompletionAssessment(
                status="turn_limit",
                confidence=1.0,
                public_rationale="The configured simulation turn limit was reached.",
                unresolved_goals=observation.persona.goals,
            )
        payload = {
            "observation": observation.model_dump(mode="json"),
            "last_action": None if last_action is None else last_action.model_dump(mode="json"),
        }
        raw = await self._client.complete_json(
            task="simulated_player.assess_completion",
            messages=[
                PiMessage(
                    role="system",
                    content=(
                        "Assess whether this simulated TRPG player would keep playing. "
                        "Use only the visible transcript and explicit player goals. Return a compact JSON assessment."
                    ),
                ),
                PiMessage(role="user", content=orjson.dumps(payload).decode("utf-8")),
            ],
            json_schema=CompletionAssessment.model_json_schema(),
            trace_id=trace_id,
        )
        return CompletionAssessment.model_validate(raw)
