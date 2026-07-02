from __future__ import annotations

from typing import Any


class SimulationReportBuilder:
    def build_markdown(self, *, run: dict[str, Any], turns: list[dict[str, Any]]) -> str:
        title = run.get("report", {}).get("title") if isinstance(run.get("report"), dict) else None
        lines = [f"# {title or '模拟跑团战报'}", ""]
        lines.extend(
            [
                f"- 运行 ID：`{run.get('id')}`",
                f"- 会话 ID：`{run.get('session_id')}`",
                f"- 玩家 Actor ID：`{run.get('actor_id')}`",
                f"- 状态：`{_status_label(run.get('status'))}`",
                "",
            ]
        )
        persona = run.get("persona")
        if isinstance(persona, dict):
            lines.extend(
                [
                    "## 模拟玩家",
                    "",
                    f"- 名称：{persona.get('name')}",
                    f"- 原型：{persona.get('archetype')}",
                    f"- 游玩风格：{persona.get('play_style')}",
                    f"- 风险偏好：{_risk_label(persona.get('risk_tolerance'))}",
                    "",
                ]
            )
        lines.extend(["## 回合记录", ""])
        for item in turns:
            notes = item.get("player_notes") if isinstance(item.get("player_notes"), dict) else {}
            gm_result = item.get("gm_result") if isinstance(item.get("gm_result"), dict) else {}
            completion = item.get("completion") if isinstance(item.get("completion"), dict) else {}
            lines.extend(
                [
                    f"### 第 {item.get('turn_index')} 回合",
                    "",
                    f"**玩家行动：** {item.get('player_action')}",
                    "",
                    f"**意图：** {notes.get('intent', '-')}",
                    "",
                    f"**玩家说明：** {notes.get('public_rationale', '-')}",
                    "",
                    f"**GM 回应：** {gm_result.get('narration', '-')}",
                    "",
                    f"**已提交事件：** {', '.join(_event_types(item.get('committed_events'))) or '-'}",
                    "",
                    f"**完成度评估：** {_status_label(completion.get('status'))} — {completion.get('public_rationale', '-')}",
                    "",
                ]
            )
        final_status = _final_status(turns)
        lines.extend(["## 最终结果", "", final_status, ""])
        return "\n".join(lines)

    def build_json(self, *, run: dict[str, Any], turns: list[dict[str, Any]], markdown: str) -> dict[str, Any]:
        return {
            "title": "模拟跑团战报",
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
        return "没有记录任何回合。"
    completion = turns[-1].get("completion")
    if isinstance(completion, dict):
        return f"最终状态：`{_status_label(completion.get('status', 'unknown'))}`。{completion.get('public_rationale', '')}"
    return "最终状态：未知。"


def _status_label(value: Any) -> str:
    labels = {
        "running": "运行中 (running)",
        "stopped": "已停止 (stopped)",
        "completed": "已完成 (completed)",
        "continue": "继续 (continue)",
        "stuck": "卡住 (stuck)",
        "unsafe": "不安全 (unsafe)",
        "turn_limit": "达到回合上限 (turn_limit)",
    }
    if isinstance(value, str):
        return labels.get(value, value)
    return "-"


def _risk_label(value: Any) -> str:
    labels = {
        "low": "低",
        "medium": "中",
        "high": "高",
    }
    if isinstance(value, str):
        return labels.get(value, value)
    return "-"
