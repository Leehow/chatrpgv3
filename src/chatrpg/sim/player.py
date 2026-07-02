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
                        "你模拟一名真实的人类 TRPG 玩家。你只知道玩家可见的跑团记录。"
                        "行动时要有好奇心、谨慎感、不完美记忆、社交推理和场景目标。"
                        "不要使用隐藏 GM 知识，不要靠猜秘密来速通。"
                        "选择一个简洁的玩家行动。"
                        "所有自然语言字段必须使用中文；不要输出英文行动、英文意图或英文理由。"
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
                public_rationale="已达到配置的模拟回合上限。",
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
                        "评估这名模拟 TRPG 玩家是否会继续游玩。"
                        "只使用玩家可见记录和明确的玩家目标。返回紧凑的 JSON 评估。"
                        "所有自然语言字段必须使用中文；不要输出英文评估、英文理由或英文目标描述。"
                    ),
                ),
                PiMessage(role="user", content=orjson.dumps(payload).decode("utf-8")),
            ],
            json_schema=CompletionAssessment.model_json_schema(),
            trace_id=trace_id,
        )
        return CompletionAssessment.model_validate(raw)
