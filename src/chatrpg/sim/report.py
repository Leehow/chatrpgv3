from __future__ import annotations

from typing import Any


class SimulationReportBuilder:
    def build_markdown(self, *, run: dict[str, Any], turns: list[dict[str, Any]]) -> str:
        title = run.get("report", {}).get("title") if isinstance(run.get("report"), dict) else None
        lines = [f"# {title or 'Simulation Battle Report'}", ""]
        lines.extend(
            [
                f"- Run ID: `{run.get('id')}`",
                f"- Session ID: `{run.get('session_id')}`",
                f"- Actor ID: `{run.get('actor_id')}`",
                f"- Status: `{run.get('status')}`",
                "",
            ]
        )
        persona = run.get("persona")
        if isinstance(persona, dict):
            lines.extend(
                [
                    "## Simulated Player",
                    "",
                    f"- Name: {persona.get('name')}",
                    f"- Archetype: {persona.get('archetype')}",
                    f"- Play style: {persona.get('play_style')}",
                    f"- Risk tolerance: {persona.get('risk_tolerance')}",
                    "",
                ]
            )
        lines.extend(["## Turn Log", ""])
        for item in turns:
            notes = item.get("player_notes") if isinstance(item.get("player_notes"), dict) else {}
            gm_result = item.get("gm_result") if isinstance(item.get("gm_result"), dict) else {}
            completion = item.get("completion") if isinstance(item.get("completion"), dict) else {}
            lines.extend(
                [
                    f"### Turn {item.get('turn_index')}",
                    "",
                    f"**Player action:** {item.get('player_action')}",
                    "",
                    f"**Intent:** {notes.get('intent', '-')}",
                    "",
                    f"**Player note:** {notes.get('public_rationale', '-')}",
                    "",
                    f"**GM response:** {gm_result.get('narration', '-')}",
                    "",
                    f"**Committed events:** {', '.join(_event_types(item.get('committed_events'))) or '-'}",
                    "",
                    f"**Completion assessment:** {completion.get('status', '-')} — {completion.get('public_rationale', '-')}",
                    "",
                ]
            )
        final_status = _final_status(turns)
        lines.extend(["## Final Outcome", "", final_status, ""])
        return "\n".join(lines)

    def build_json(self, *, run: dict[str, Any], turns: list[dict[str, Any]], markdown: str) -> dict[str, Any]:
        return {
            "title": "Simulation Battle Report",
            "run_id": run.get("id"),
            "session_id": run.get("session_id"),
            "status": run.get("status"),
            "turn_count": len(turns),
            "markdown": markdown,
        }


def _event_types(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, dict) and isinstance(item.get("event_type"), str):
            result.append(item["event_type"])
    return result


def _final_status(turns: list[dict[str, Any]]) -> str:
    if not turns:
        return "No turns were recorded."
    completion = turns[-1].get("completion")
    if isinstance(completion, dict):
        return f"Final status: `{completion.get('status', 'unknown')}`. {completion.get('public_rationale', '')}"
    return "Final status: unknown."
