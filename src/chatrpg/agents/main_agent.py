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
                    "玩家声明的是意图和方法，不是权威骰点或成功等级。"
                    "如果玩家行动在当前 TRPG 中显然需要规则结算，请设置 procedure_id 和结构化 inputs，"
                    "例如 coc7e.skill_roll 使用 inputs.skill_id、difficulty、reason；coc7e.sanity_roll 使用 loss specs。"
                    "不要把玩家声称的骰点、成功、大成功、失败或伤害结果写入 inputs；这些必须由 runtime 掷骰和提交。"
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
                    "你不掷骰、不接受玩家声称的骰点、不根据未提交的玩家骰点判定成功或失败。"
                    "骰点、成功等级、SAN 损失、伤害、追逐位移和资源变化只能来自已提交的 runtime 结算事件，"
                    "例如 SkillRollResolved、SanityRollResolved、AttackResolved、ResolutionRecorded 或 procedure_result。"
                    "如果存在 runtime 结算，必须显式说明使用的规则、骰子、掷出结果、阈值和最终结论；不要重新解释成另一个结果。"
                    "如果玩家声称自己掷出某个结果，但 committed_events 没有对应 runtime 结算，要明确该结果无效，等待 runtime 掷骰结算。"
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
