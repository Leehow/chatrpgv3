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
    assert "**玩家行动：** 我检查书桌。" in report
    assert "Simulation Battle Report" not in report
    assert "Player action" not in report
