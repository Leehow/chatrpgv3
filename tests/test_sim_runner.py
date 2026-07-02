import asyncio
from types import SimpleNamespace
from typing import Any

from chatrpg.sim.models import (
    CompletionAssessment,
    PlayerPersona,
    SimConfig,
    SimulatedPlayerAction,
)
from chatrpg.sim.runner import SimulationRunner


class _DumpableIntent:
    def model_dump(self, mode: str = "json") -> dict[str, str]:
        return {"intent": "inspect"}


class _FakePlayer:
    async def choose_action(self, observation: object, *, trace_id: str) -> SimulatedPlayerAction:
        return SimulatedPlayerAction(
            action="我检查房间。",
            intent="调查",
            confidence=0.9,
            public_rationale="房间里可能有线索。",
        )

    async def assess_completion(
        self,
        *,
        observation: object,
        last_action: SimulatedPlayerAction | None,
        turn_limit_reached: bool,
        trace_id: str,
    ) -> CompletionAssessment:
        return CompletionAssessment(
            status="turn_limit",
            confidence=1.0,
            public_rationale="已达到配置的模拟回合上限。",
            unresolved_goals=["理解谜团"],
        )


class _FakeGm:
    async def turn(self, *, session_id: str, message: str, actor_id: str | None = None) -> object:
        return SimpleNamespace(
            trace_id="trc_gm",
            intent=_DumpableIntent(),
            narration=SimpleNamespace(text="你发现了一张落满灰尘的收据。"),
            clue_decision=None,
            committed_events=[],
        )


class _FakeRecorder:
    def __init__(self) -> None:
        self.run: dict[str, Any] = {}
        self.turns: list[dict[str, Any]] = []

    async def start_run(self, *, config: SimConfig, persona: PlayerPersona, trace_id: str) -> str:
        self.run = {
            "id": "sim1",
            "session_id": config.session_id,
            "actor_id": config.actor_id,
            "persona": persona.model_dump(mode="json"),
            "config": config.model_dump(mode="json"),
            "status": "running",
            "report": {},
            "trace_id": trace_id,
        }
        return "sim1"

    async def record_turn(
        self,
        *,
        run_id: str,
        turn_index: int,
        player_action: SimulatedPlayerAction,
        gm_result: dict[str, Any],
        committed_events: list[dict[str, Any]],
        completion: CompletionAssessment,
        trace_id: str,
    ) -> str:
        self.turns.append(
            {
                "id": "stn1",
                "run_id": run_id,
                "turn_index": turn_index,
                "player_action": player_action.action,
                "player_notes": player_action.model_dump(mode="json"),
                "gm_result": gm_result,
                "committed_events": committed_events,
                "completion": completion.model_dump(mode="json"),
                "trace_id": trace_id,
            }
        )
        return "stn1"

    async def load_run(self, *, run_id: str) -> dict[str, Any] | None:
        return dict(self.run)

    async def load_turns(self, *, run_id: str) -> list[dict[str, Any]]:
        return list(self.turns)

    async def finish_run(self, *, run_id: str, status: str, report: dict[str, Any]) -> None:
        self.run["status"] = status
        self.run["report"] = report


def test_runner_report_uses_finished_status() -> None:
    async def run() -> str:
        summary = await SimulationRunner(
            player=_FakePlayer(),
            gm=_FakeGm(),
            recorder=_FakeRecorder(),
            event_store=object(),
        ).run(
            config=SimConfig(session_id="ses1", max_turns=1, auto_create_character=False),
            persona=PlayerPersona(),
        )
        assert summary.report_markdown is not None
        return summary.report_markdown

    report = asyncio.run(run())

    assert "- 状态：`已停止 (stopped)`" in report
    assert "- 状态：`运行中 (running)`" not in report
