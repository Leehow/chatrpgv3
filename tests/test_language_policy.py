import asyncio
from typing import Any

from chatrpg.agents.contracts import NarrationRequest, PlayerInput
from chatrpg.agents.main_agent import PiMainAgent
from chatrpg.agents.pi_client import PiMessage
from chatrpg.sim.models import PlayerPersona, SimPlayerObservation, SimulatedPlayerAction
from chatrpg.sim.player import SimulatedPlayerAgent


class _RecordingClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    async def complete_json(
        self,
        *,
        task: str,
        messages: list[PiMessage],
        json_schema: dict[str, Any],
        trace_id: str,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "task": task,
                "messages": messages,
                "json_schema": json_schema,
                "trace_id": trace_id,
            }
        )
        return self.payload


def test_main_agent_prompts_require_chinese_output() -> None:
    async def run() -> list[str]:
        client = _RecordingClient(
            {
                "intent": "调查",
                "targets": [],
                "confidence": 1.0,
                "needs_clarification": False,
            }
        )
        agent = PiMainAgent(client)
        await agent.resolve_intent(PlayerInput(session_id="ses1", message="调查书桌"), trace_id="trc1")

        client.payload = {"text": "你谨慎地检查书桌。", "source_refs": []}
        await agent.narrate(NarrationRequest(session_id="ses1"), trace_id="trc2")
        return [call["messages"][0].content for call in client.calls]

    prompts = asyncio.run(run())

    assert all("中文" in prompt for prompt in prompts)
    assert all("English" not in prompt for prompt in prompts)


def test_simulated_player_prompts_require_chinese_output() -> None:
    async def run() -> list[str]:
        client = _RecordingClient(
            {
                "action": "我先观察房间。",
                "intent": "调查",
                "confidence": 0.9,
                "public_rationale": "先确认可见线索。",
                "human_behavior_notes": [],
                "wants_to_stop": False,
                "stop_reason": None,
            }
        )
        player = SimulatedPlayerAgent(client)
        observation = SimPlayerObservation(
            session_id="ses1",
            turn_index=1,
            persona=PlayerPersona(),
        )
        await player.choose_action(observation, trace_id="trc1")

        client.payload = {
            "status": "continue",
            "confidence": 0.8,
            "public_rationale": "还有线索要追。",
            "unresolved_goals": [],
        }
        await player.assess_completion(
            observation=observation,
            last_action=SimulatedPlayerAction(
                action="我先观察房间。",
                intent="调查",
                confidence=0.9,
                public_rationale="先确认可见线索。",
            ),
            turn_limit_reached=False,
            trace_id="trc2",
        )
        return [call["messages"][0].content for call in client.calls]

    prompts = asyncio.run(run())

    assert all("中文" in prompt for prompt in prompts)
    assert all("English" not in prompt for prompt in prompts)
