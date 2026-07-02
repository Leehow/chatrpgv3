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
