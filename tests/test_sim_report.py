from chatrpg.sim.report import SimulationReportBuilder


def test_simulation_report_builder_includes_turns() -> None:
    run = {
        "id": "sim1",
        "session_id": "ses1",
        "actor_id": "sim_player",
        "status": "completed",
        "persona": {
            "name": "Tester",
            "archetype": "investigator",
            "play_style": "careful",
            "risk_tolerance": "medium",
        },
        "report": {"title": "Case Report"},
    }
    turns = [
        {
            "turn_index": 1,
            "player_action": "I inspect the desk.",
            "player_notes": {"intent": "investigate", "public_rationale": "The desk may hold records."},
            "gm_result": {"narration": "You find a receipt."},
            "committed_events": [{"event_type": "ClueDiscovered"}],
            "completion": {"status": "continue", "public_rationale": "More leads remain."},
        }
    ]
    report = SimulationReportBuilder().build_markdown(run=run, turns=turns)
    assert "Case Report" in report
    assert "I inspect the desk." in report
    assert "ClueDiscovered" in report


def test_simulation_report_builder_uses_chinese_template_by_default() -> None:
    run = {
        "id": "sim1",
        "session_id": "ses1",
        "actor_id": "sim_player",
        "status": "stopped",
        "persona": {
            "name": "谨慎调查员",
            "archetype": "调查员",
            "play_style": "谨慎",
            "risk_tolerance": "medium",
        },
        "report": {},
    }
    turns = [
        {
            "turn_index": 1,
            "player_action": "我检查书桌。",
            "player_notes": {"intent": "调查", "public_rationale": "书桌可能有线索。"},
            "gm_result": {"narration": "你发现了一张收据。"},
            "committed_events": [{"event_type": "ClueDiscovered"}],
            "completion": {"status": "continue", "public_rationale": "还有线索。"},
        }
    ]

    report = SimulationReportBuilder().build_markdown(run=run, turns=turns)

    assert "# 模拟跑团战报" in report
    assert "## 模拟玩家" in report
    assert "**玩家发言：** 我检查书桌。" in report
    assert "玩家说明" not in report
    assert "书桌可能有线索。" not in report
    assert "Simulation Battle Report" not in report
    assert "Player action" not in report


def test_simulation_report_builder_renders_full_character_sheet_from_character_created_event() -> None:
    run = {"id": "sim1", "session_id": "ses1", "actor_id": "sim_player", "status": "stopped", "report": {}}
    turns = [
        {
            "turn_index": 0,
            "player_action": "创建角色。",
            "player_notes": {"intent": "character_creation", "public_rationale": "开局需要角色。"},
            "gm_result": {"narration": "已创建角色。"},
            "committed_events": [
                {
                    "event_type": "CharacterCreated",
                    "payload": {
                        "id": "pc1",
                        "name": "Harvey Walters",
                        "owner": "sim_player",
                        "resources": {"hp": 12, "hp_max": 12, "mp": 12, "mp_max": 12, "sanity": 60, "sanity_max": 99, "luck": 45},
                        "traits": {
                            "age": 30,
                            "occupation": "antiquarian",
                            "residence": "1920s Boston",
                            "str": 50,
                            "str_half": 25,
                            "str_fifth": 10,
                            "con": 60,
                            "con_half": 30,
                            "con_fifth": 12,
                            "siz": 60,
                            "siz_half": 30,
                            "siz_fifth": 12,
                            "dex": 50,
                            "dex_half": 25,
                            "dex_fifth": 10,
                            "app": 50,
                            "app_half": 25,
                            "app_fifth": 10,
                            "int": 70,
                            "int_half": 35,
                            "int_fifth": 14,
                            "pow": 60,
                            "pow_half": 30,
                            "pow_fifth": 12,
                            "edu": 80,
                            "edu_half": 40,
                            "edu_fifth": 16,
                            "move": 8,
                            "damage_bonus": "0",
                            "build": 0,
                            "personal_interest_points": 140,
                            "gear": "notebook",
                            "weapons": "none",
                            "skill_thresholds": {"library_use": {"regular": 70, "hard": 35, "extreme": 14}},
                        },
                        "skills": {"library_use": 70, "spot_hidden": 60},
                        "conditions": [],
                    },
                }
            ],
            "completion": {"status": "continue", "public_rationale": "继续。"},
        }
    ]

    report = SimulationReportBuilder().build_markdown(run=run, turns=turns)

    assert "## 角色卡" in report
    assert "### Harvey Walters" in report
    assert "| STR | 50 | 25 | 10 |" in report
    assert "| HP | 12 / 12 |" in report
    assert "| library_use | 70 | 35 | 14 |" in report
    assert "**装备：** notebook" in report
    assert "**武器：** none" in report


def test_simulation_report_builder_renders_authoritative_resolution_trace() -> None:
    run = {"id": "sim1", "session_id": "ses1", "actor_id": "sim_player", "status": "stopped", "report": {}}
    turns = [
        {
            "turn_index": 2,
            "player_action": "我查阅档案。",
            "player_notes": {"intent": "调查", "public_rationale": "需要检索资料。"},
            "gm_result": {"narration": "Runtime 已结算。"},
            "committed_events": [
                {
                    "event_type": "SkillRollResolved",
                    "payload": {
                        "resolution": {
                            "kind": "coc7e.skill_roll",
                            "title": "CoC 7e 检定：图书馆利用",
                            "rules": [
                                {
                                    "rule_id": "coc7e.success_thresholds",
                                    "label": "成功等级阈值",
                                    "formula": "regular=skill, hard=floor(skill/2), extreme=floor(skill/5)",
                                    "inputs": {"skill": 70},
                                    "output": 70,
                                }
                            ],
                            "dice": [
                                {
                                    "notation": "1D100",
                                    "value": 42,
                                    "unit_die": 2,
                                    "tens_dice": [4],
                                    "selected_tens": 4,
                                    "bonus_dice": 0,
                                    "penalty_dice": 0,
                                    "reason": "图书馆利用",
                                }
                            ],
                            "outcome": {"passed": True, "level": "regular", "roll": 42, "target": 70},
                        }
                    },
                }
            ],
            "completion": {"status": "continue", "public_rationale": "继续。"},
        }
    ]

    report = SimulationReportBuilder().build_markdown(run=run, turns=turns)

    assert "**规则结算：**" in report
    assert "CoC 7e 检定：图书馆利用" in report
    assert "骰子：1D100" in report
    assert "最终 42" in report
    assert "'passed': True" in report
