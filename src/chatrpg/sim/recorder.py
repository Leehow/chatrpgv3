from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from chatrpg.core.ids import new_id
from chatrpg.sim.models import CompletionAssessment, PlayerPersona, SimConfig, SimulatedPlayerAction


class SimulationRecorder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start_run(self, *, config: SimConfig, persona: PlayerPersona, trace_id: str) -> str:
        run_id = new_id("sim")
        await self._session.execute(
            text(
                """
                insert into simulation_runs (id, session_id, actor_id, persona, config, status, trace_id)
                values (:id, :session_id, :actor_id, cast(:persona as jsonb), cast(:config as jsonb), :status, :trace_id)
                """
            ),
            {
                "id": run_id,
                "session_id": config.session_id,
                "actor_id": config.actor_id,
                "persona": persona.model_dump_json(),
                "config": config.model_dump_json(),
                "status": "running",
                "trace_id": trace_id,
            },
        )
        return run_id

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
        row_id = new_id("stn")
        await self._session.execute(
            text(
                """
                insert into simulation_turns
                  (id, run_id, turn_index, player_action, player_notes, gm_result, committed_events, completion, trace_id)
                values
                  (:id, :run_id, :turn_index, :player_action, cast(:player_notes as jsonb), cast(:gm_result as jsonb),
                   cast(:committed_events as jsonb), cast(:completion as jsonb), :trace_id)
                """
            ),
            {
                "id": row_id,
                "run_id": run_id,
                "turn_index": turn_index,
                "player_action": player_action.action,
                "player_notes": player_action.model_dump_json(),
                "gm_result": _json_dump(gm_result),
                "committed_events": _json_dump(committed_events),
                "completion": completion.model_dump_json(),
                "trace_id": trace_id,
            },
        )
        return row_id

    async def finish_run(self, *, run_id: str, status: str, report: dict[str, Any]) -> None:
        await self._session.execute(
            text(
                """
                update simulation_runs
                set status = :status,
                    report = cast(:report as jsonb),
                    completed_at = now()
                where id = :id
                """
            ),
            {"id": run_id, "status": status, "report": _json_dump(report)},
        )

    async def load_run(self, *, run_id: str) -> dict[str, Any] | None:
        row = (
            await self._session.execute(
                text("select id, session_id, actor_id, persona, config, status, report, trace_id, created_at, completed_at from simulation_runs where id = :id"),
                {"id": run_id},
            )
        ).mappings().one_or_none()
        return None if row is None else dict(row)

    async def load_turns(self, *, run_id: str) -> list[dict[str, Any]]:
        rows = (
            await self._session.execute(
                text(
                    """
                    select id, run_id, turn_index, player_action, player_notes, gm_result,
                           committed_events, completion, trace_id, created_at
                    from simulation_turns
                    where run_id = :run_id
                    order by turn_index
                    """
                ),
                {"run_id": run_id},
            )
        ).mappings()
        return [dict(row) for row in rows]


def _json_dump(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)
