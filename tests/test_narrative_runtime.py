from chatrpg.runtime.narrative import NarrativeRuntime
from chatrpg.runtime.progress import ProgressSnapshot


def test_narrative_runtime_plans_opening_investigation() -> None:
    progress = ProgressSnapshot(
        phase="opening",
        pressure="low",
        completion_ratio=0.0,
    )
    plan = NarrativeRuntime().plan(progress=progress)
    assert plan.recommended_functions == ["orient", "investigate"]
    assert "confront" in plan.avoid_functions


def test_narrative_runtime_plans_climax_pressure() -> None:
    progress = ProgressSnapshot(
        phase="climax",
        pressure="high",
        known_revelation_ids=["r1", "r2", "r3"],
        completion_ratio=0.9,
    )
    plan = NarrativeRuntime().plan(progress=progress)
    assert "confront" in plan.recommended_functions
    assert "SanityRollResolved" in plan.required_event_types
