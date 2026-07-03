from __future__ import annotations

from typing import Any

_CHARACTERISTIC_ORDER = ["str", "con", "siz", "dex", "app", "int", "pow", "edu"]
_CHARACTERISTIC_LABELS = {
    "str": "STR",
    "con": "CON",
    "siz": "SIZ",
    "dex": "DEX",
    "app": "APP",
    "int": "INT",
    "pow": "POW",
    "edu": "EDU",
}
_BACKGROUND_FIELDS = {
    "age": "年龄",
    "occupation": "职业",
    "residence": "居住地",
    "birthplace": "出生地",
    "sex": "性别",
    "gender": "性别认同",
    "personal_description": "个人描述",
    "ideology_beliefs": "信念 / 意识形态",
    "significant_people": "重要人物",
    "meaningful_locations": "重要地点",
    "treasured_possessions": "珍贵物品",
    "traits": "特质",
    "injuries_scars": "伤疤 / 旧伤",
    "phobias_manias": "恐惧症 / 躁狂症",
    "cash": "现金",
    "spending_level": "消费水平",
    "assets": "资产",
    "gear": "装备",
    "weapons": "武器",
}
_RESOURCE_LABELS = {
    "hp": "HP",
    "mp": "MP",
    "sanity": "SAN",
    "luck": "Luck",
}
_DERIVED_FIELDS = {
    "move": "MOV",
    "damage_bonus": "Damage Bonus",
    "build": "Build",
    "personal_interest_points": "Personal Interest Points",
}


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
        character_sheet_lines = _character_sheets_from_turns(turns)
        if character_sheet_lines:
            lines.extend(["## 角色卡", "", *character_sheet_lines, ""])
        lines.extend(["## 回合记录", ""])
        for item in turns:
            gm_result = item.get("gm_result") if isinstance(item.get("gm_result"), dict) else {}
            completion = item.get("completion") if isinstance(item.get("completion"), dict) else {}
            resolution_lines = _resolution_lines(item.get("committed_events"))
            trace_lines = _agent_trace_lines(gm_result.get("agent_trace"))
            lines.extend(
                [
                    f"### 第 {item.get('turn_index')} 回合",
                    "",
                    f"**玩家发言：** {item.get('player_action')}",
                    "",
                    f"**GM 回应：** {gm_result.get('narration', '-')}",
                    "",
                ]
            )
            if trace_lines:
                lines.extend(["**GM 执行轨迹：**", "", *trace_lines, ""])
            if resolution_lines:
                lines.extend(["**规则结算：**", "", *resolution_lines, ""])
            lines.extend(
                [
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
            "characters": _character_sheet_json_from_turns(turns),
            "resolutions": _resolution_json_from_turns(turns),
            "agent_traces": _agent_trace_json_from_turns(turns),
        }


def _character_sheets_from_turns(turns: list[dict[str, Any]]) -> list[str]:
    characters = _character_payloads_from_turns(turns)
    lines: list[str] = []
    for payload in characters:
        lines.extend(_render_character_sheet(payload))
        lines.append("")
    return lines


def _character_sheet_json_from_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _character_payloads_from_turns(turns)


def _character_payloads_from_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    characters: list[dict[str, Any]] = []
    for item in turns:
        committed_events = item.get("committed_events")
        if not isinstance(committed_events, list):
            continue
        for event in committed_events:
            if not isinstance(event, dict) or event.get("event_type") != "CharacterCreated":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            character_id = payload.get("id")
            stable_id = character_id if isinstance(character_id, str) else str(len(characters))
            if stable_id in seen:
                continue
            seen.add(stable_id)
            characters.append(payload)
    return characters


def _render_character_sheet(payload: dict[str, Any]) -> list[str]:
    resources = _dict(payload.get("resources"))
    traits = _dict(payload.get("traits"))
    skills = _int_dict(payload.get("skills"))
    conditions = payload.get("conditions") if isinstance(payload.get("conditions"), list) else []
    lines = [f"### {_text(payload.get('name'), '未命名角色')}", ""]
    lines.extend(_identity_lines(payload=payload, traits=traits))
    lines.extend(_resource_lines(resources))
    lines.extend(_characteristic_lines(traits))
    lines.extend(_derived_lines(traits))
    lines.extend(_skill_lines(skills=skills, traits=traits))
    lines.extend(_background_lines(traits=traits, conditions=conditions))
    return lines


def _identity_lines(*, payload: dict[str, Any], traits: dict[str, Any]) -> list[str]:
    entries = [
        ("角色 ID", payload.get("id")),
        ("玩家", payload.get("owner")),
        ("职业", traits.get("occupation")),
        ("年龄", traits.get("age")),
        ("居住地", traits.get("residence")),
    ]
    return _key_value_section("身份", entries)


def _resource_lines(resources: dict[str, Any]) -> list[str]:
    rows = []
    for key, label in _RESOURCE_LABELS.items():
        value = resources.get(key)
        maximum = resources.get(f"{key}_max")
        display = f"{value} / {maximum}" if maximum is not None else value
        rows.append((label, display))
    return _table_section("资源", ["项目", "数值"], rows)


def _characteristic_lines(traits: dict[str, Any]) -> list[str]:
    rows = []
    threshold_map = _dict(traits.get("characteristic_thresholds"))
    for key in _CHARACTERISTIC_ORDER:
        value = traits.get(key)
        thresholds = _dict(threshold_map.get(key))
        half = traits.get(f"{key}_half", thresholds.get("hard"))
        fifth = traits.get(f"{key}_fifth", thresholds.get("extreme"))
        rows.append((_CHARACTERISTIC_LABELS[key], value, half, fifth))
    return _table_section("属性", ["属性", "全值", "半值", "五分之一"], rows)


def _derived_lines(traits: dict[str, Any]) -> list[str]:
    return _key_value_section("派生值", [(label, traits.get(key)) for key, label in _DERIVED_FIELDS.items()])


def _skill_lines(*, skills: dict[str, int], traits: dict[str, Any]) -> list[str]:
    skill_thresholds = _dict(traits.get("skill_thresholds"))
    rows = []
    for skill_id, value in sorted(skills.items(), key=lambda item: (-item[1], item[0])):
        thresholds = _dict(skill_thresholds.get(skill_id))
        hard = thresholds.get("hard", value // 2)
        extreme = thresholds.get("extreme", value // 5)
        rows.append((skill_id, value, hard, extreme))
    return _table_section("技能", ["技能", "全值", "半值", "五分之一"], rows)


def _background_lines(*, traits: dict[str, Any], conditions: list[Any]) -> list[str]:
    entries = [(label, traits.get(key)) for key, label in _BACKGROUND_FIELDS.items() if key not in {"age", "occupation", "residence"}]
    if conditions:
        entries.append(("状态 / 条件", ", ".join(str(item) for item in conditions)))
    else:
        entries.append(("状态 / 条件", "无"))
    return _key_value_section("背景、装备与状态", entries)


def _resolution_json_from_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in turns:
        turn_index = item.get("turn_index")
        for resolution in _resolution_payloads(item.get("committed_events")):
            results.append({"turn_index": turn_index, "resolution": resolution})
    return results


def _resolution_lines(events: Any) -> list[str]:
    lines: list[str] = []
    for resolution in _resolution_payloads(events):
        lines.extend(_render_resolution(resolution))
        lines.append("")
    return lines


def _resolution_payloads(events: Any) -> list[dict[str, Any]]:
    if not isinstance(events, list):
        return []
    results: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        resolution = payload.get("resolution")
        if isinstance(resolution, dict):
            results.append(resolution)
            continue
        for nested_key in ("attack", "damage"):
            nested = payload.get(nested_key)
            if isinstance(nested, dict) and isinstance(nested.get("resolution"), dict):
                results.append(nested["resolution"])
    return results


def _render_resolution(resolution: dict[str, Any]) -> list[str]:
    lines = [f"- **{_text(resolution.get('title'), 'Runtime 结算')}**"]
    for rule in _list_of_dicts(resolution.get("rules")):
        lines.append(
            "  - 规则："
            f"{_text(rule.get('label'), '-')}；公式：`{_text(rule.get('formula'), '-')}`；"
            f"输入：`{_text(rule.get('inputs'), '{}')}`；输出：`{_text(rule.get('output'), '-')}`"
        )
    for dice in _list_of_dicts(resolution.get("dice")):
        lines.append(f"  - 骰子：{_dice_text(dice)}")
    outcome = resolution.get("outcome")
    if isinstance(outcome, dict) and outcome:
        lines.append(f"  - 结论：`{outcome}`")
    return lines


def _agent_trace_json_from_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in turns:
        gm_result = item.get("gm_result") if isinstance(item.get("gm_result"), dict) else {}
        trace = gm_result.get("agent_trace")
        if isinstance(trace, list):
            results.append({"turn_index": item.get("turn_index"), "steps": trace})
    return results


def _agent_trace_lines(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        step = item.get("step")
        stage = _text(item.get("stage"), "步骤")
        summary = _text(item.get("summary"), "-")
        data = item.get("data")
        detail = f"；数据：`{data}`" if isinstance(data, dict) and data else ""
        lines.append(f"- 第 {step} 步 / {stage}：{summary}{detail}")
    return lines


def _dice_text(dice: dict[str, Any]) -> str:
    notation = _text(dice.get("notation"), "dice")
    if "value" in dice:
        return (
            f"{notation}；个位 {dice.get('unit_die')}；十位候选 {dice.get('tens_dice')}；"
            f"选中十位 {dice.get('selected_tens')}；最终 {dice.get('value')}"
        )
    return f"{notation}；掷出 {dice.get('rolls')}；修正 {dice.get('modifier', 0)}；总计 {dice.get('total')}"


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _key_value_section(title: str, entries: list[tuple[str, Any]]) -> list[str]:
    visible = [(key, value) for key, value in entries if _has_value(value)]
    if not visible:
        return []
    lines = [f"#### {title}", ""]
    for key, value in visible:
        lines.append(f"- **{key}：** {_text(value, '-')}")
    lines.append("")
    return lines


def _table_section(title: str, headers: list[str], rows: list[tuple[Any, ...]]) -> list[str]:
    visible_rows = [row for row in rows if any(_has_value(value) for value in row[1:])]
    if not visible_rows:
        return []
    lines = [f"#### {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in visible_rows:
        lines.append("| " + " | ".join(_text(value, "-") for value in row) + " |")
    lines.append("")
    return lines


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_dict(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items() if isinstance(item, int)}


def _has_value(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _text(value: Any, fallback: str) -> str:
    if not _has_value(value):
        return fallback
    return str(value)


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
