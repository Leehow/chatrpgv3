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
                        "你模拟一名真实的人类 TRPG 玩家，而不是给 GM 写分析报告。"
                        "你只知道玩家可见的跑团记录、自己的角色卡、资源、技能、状态和 persona。"
                        "先在 private_reasoning 中简短判断：当前目标、已知线索、角色擅长项、风险、下一步如何推进。"
                        "action 字段才是发给 Keeper/GM 的真实玩家发言：必须像真人聊天，一般一两句话，只做一件具体事。"
                        "不要把 private_reasoning、动机分析、长篇计划或元说明写进 action。"
                        "不要替系统掷骰，不要声称掷出了某个骰点，不要写‘我大成功’或‘我造成伤害’。"
                        "如果需要检定，action 只说你想怎么做、用什么方式做，让 Keeper/runtime 调用规则工具结算。"
                        "要积极推进剧情：优先追随刚出现的线索、提出明确问题、移动到明确地点、和 NPC 交谈或使用角色强项。"
                        "避免空泛地要求‘请导入剧情’或‘我整理角色卡’，除非当前确实没有任何场景。"
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
