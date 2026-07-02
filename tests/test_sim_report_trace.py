from chatrpg.sim.report import SimulationReportBuilder


def test_simulation_report_renders_public_gm_trace() -> None:
    run = {"id": "sim1", "session_id": "ses1", "actor_id": "sim_player", "status": "stopped", "report": {}}
    turns = [
        {
            "turn_index": 1,
            "player_action": "我查阅档案。",
            "gm_result": {
                "narration": "开始检索。",
                "agent_trace": [
                    {"step": 1, "stage": "分析玩家意图", "summary": "识别为资料检索。", "data": {"procedure_id": "coc7e.skill_roll"}},
                    {"step": 2, "stage": "调用规则工具", "summary": "执行图书馆使用检定。", "data": {"event_types": ["SkillRollResolved"]}},
                ],
            },
            "committed_events": [{"event_type": "SkillRollResolved", "payload": {}}],
            "completion": {"status": "continue", "public_rationale": "继续。"},
        }
    ]

    report = SimulationReportBuilder().build_markdown(run=run, turns=turns)

    assert "**GM 执行轨迹：**" in report
    assert "第 1 步 / 分析玩家意图" in report
    assert "第 2 步 / 调用规则工具" in report
