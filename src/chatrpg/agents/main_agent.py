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
                    "你是一个源材料可追溯 TRPG runtime 的 ReAct 风格 GM 意图解释器。"
                    "你不改变状态、不掷骰、不揭露 Keeper 专属信息。"
                    "玩家声明的是意图和方法，不是权威骰点或成功等级。"
                    "你的工作是观察 context、选择合适的 GM skill/tool、并输出结构化 IntentFrame；"
                    "不要输出隐藏推理过程，只输出 schema-valid JSON。"
                    "输入的 context 会给出当前角色、资源、技能、可用 agent_skills、可用规则 procedure、"
                    "当前调查 frontier、候选线索、pending_decisions、pending_clues、progress 和 narrative_plan。"
                    "需要规则结算时，优先选择 context.agent_skills 中的 skill，填写 skill_calls；"
                    "如果该 skill 绑定 procedure_id，也要把 IntentFrame.procedure_id 和 inputs 填成同一个 procedure。"
                    "procedure_id 必须来自 context.available_procedures 或 context.agent_skills 中的 procedure_id。"
                    "inputs 必须使用 context.party_status 中真实存在的角色 ID、技能 ID、属性 ID 和资源。"
                    "探索、侦查、社交、潜入、图书馆查阅等不确定行动通常选择 exploration/social skill；"
                    "攻击、闪避、对抗、追逐、理智、急救、医学、施法、典籍、成长分别选择对应 skill。"
                    "如果玩家表示要花费幸运、调整刚才失败的检定，且 context.pending_decisions 中有 kind=luck_spend，"
                    "选择 procedure_id=coc7e.luck_spend；可以只传 source_event_id 或 decision_id，必要时也可以不传 roll/target，runtime 会使用 pending decision。"
                    "不要把玩家声称的骰点、成功、大成功、失败或伤害结果写入 inputs；这些必须由 runtime 掷骰和提交。"
                    "如果玩家行动含糊，或缺少可用技能、目标、伤害、SAN 损失等必要输入，设置 needs_clarification=true。"
                    "如果只是纯叙事、询问、选择移动方向或不需要规则结算，procedure_id 设为 null。"
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
                    "例如 SkillRollResolved、SanityRollResolved、AttackResolved、LuckSpent、ResolutionRecorded 或 procedure_result。"
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
