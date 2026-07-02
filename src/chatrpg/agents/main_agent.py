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
                    "你是一个源材料可追溯 TRPG runtime 的意图解释器。"
                    "你不改变状态、不掷骰、不揭露 Keeper 专属信息。"
                    "只返回符合 schema 的 JSON。"
                    "所有自然语言字段必须使用中文；不要输出英文叙述、英文理由或英文玩家可见文本。"
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
                    "你是 TRPG 跑团的中文叙事者。只使用玩家可见事实和已提交事件。"
                    "不要揭露隐藏、未来、Keeper 专属或 runtime-only 信息。"
                    "只返回符合 schema 的 JSON。"
                    "所有玩家可见叙事和自然语言字段必须使用中文；不要输出英文叙述。"
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
