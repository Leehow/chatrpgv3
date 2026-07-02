from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState
from chatrpg.runtime.state import StateReducer
from chatrpg.runtime.workflow import WorkflowEngine
from chatrpg.systems.workflows import build_coc7e_workflow, build_triangle_agency_workflow


def test_workflow_bootstrap_starts_at_character_creation_without_party() -> None:
    reducer = StateReducer()
    state = reducer.initial(session_id="ses", system_id="coc7e", adventure_id="adv")
    workflow = build_coc7e_workflow()

    events = WorkflowEngine(reducer).bootstrap_events(
        session_id="ses",
        state=state,
        workflow=workflow,
        trace_id="trc",
    )
    next_state = reducer.replay(state, events)

    assert [event.event_type for event in events] == ["WorkflowPhaseEntered"]
    assert next_state.workflow_phase == "coc7e.character_creation"


def test_workflow_auto_transitions_after_party_exists() -> None:
    reducer = StateReducer()
    initial = reducer.initial(session_id="ses", system_id="coc7e", adventure_id="adv")
    state = reducer.replay(initial, [_character_event()])
    workflow = build_coc7e_workflow()

    events = WorkflowEngine(reducer).bootstrap_events(
        session_id="ses",
        state=state,
        workflow=workflow,
        trace_id="trc",
    )
    next_state = reducer.replay(state, events)

    assert [event.event_type for event in events] == [
        "WorkflowPhaseEntered",
        "WorkflowPhaseCompleted",
        "WorkflowPhaseEntered",
    ]
    assert next_state.workflow_phase == "coc7e.investigation"
    assert "coc7e.character_creation" in next_state.completed_workflow_phases


def test_triangle_workflow_has_morning_briefing_phase() -> None:
    workflow = build_triangle_agency_workflow()
    phase_ids = {phase.id for phase in workflow.phases}
    assert "triangle.agent_creation" in phase_ids
    assert "triangle.morning_briefing" in phase_ids
    assert "triangle.field_work" in phase_ids
    assert "triangle.mission_report" in phase_ids


def _character_event() -> DomainEvent:
    return DomainEvent(
        session_id="ses",
        event_type="CharacterCreated",
        actor_id="pc1",
        payload=CharacterState(id="pc1", name="Investigator").model_dump(mode="json"),
        trace_id="trc",
    )
