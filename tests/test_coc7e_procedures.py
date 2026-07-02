from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState
from chatrpg.runtime.dice import DiceEngine
from chatrpg.runtime.state import StateReducer
from chatrpg.systems.coc7e.procedures import Coc7eProcedureRunner


def test_coc7e_skill_procedure_uses_actor_skill() -> None:
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"sanity": 50, "luck": 40},
            traits={"int": 80},
            skills={"spot_hidden": 75},
        )
    )
    result = Coc7eProcedureRunner(DiceEngine(seed=1)).run(
        procedure_id="coc7e.skill_roll",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={"skill_id": "spot_hidden", "reason": "desk search"},
        trace_id="trc",
    )

    assert result.status == "completed"
    assert [event.event_type for event in result.events] == ["SkillRollResolved"]
    assert result.events[0].payload["target"] == 75
    assert result.events[0].payload["target_ref"] == {"kind": "skill", "id": "spot_hidden"}


def test_coc7e_sanity_procedure_commits_resource_and_condition_events() -> None:
    reducer = StateReducer()
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"sanity": 50, "luck": 40},
            traits={"int": 80},
            skills={"cthulhu_mythos": 0},
        )
    )
    result = Coc7eProcedureRunner(DiceEngine(seed=1)).run(
        procedure_id="coc7e.sanity_roll",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={"success_loss": {"constant": 0}, "failure_loss": {"constant": 6}, "reason": "mythos shock"},
        trace_id="trc",
    )
    next_state = reducer.replay(state, result.events)

    assert result.status == "completed"
    assert "SanityRollResolved" in [event.event_type for event in result.events]
    assert next_state.party[0].resources["sanity"] == 44
    assert "temporary_insanity" in next_state.party[0].conditions


def test_coc7e_tome_study_changes_mythos_skill() -> None:
    reducer = StateReducer()
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"sanity": 50, "luck": 40},
            traits={"int": 80},
            skills={"cthulhu_mythos": 0},
        )
    )
    result = Coc7eProcedureRunner(DiceEngine(seed=3)).run(
        procedure_id="coc7e.study_tome",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={
            "title": "Example Tome",
            "weeks_required": 2,
            "mythos_gain": 3,
            "sanity_loss": {"count": 1, "sides": 2, "modifier": -1},
        },
        trace_id="trc",
    )
    next_state = reducer.replay(state, result.events)

    assert result.status == "completed"
    assert next_state.party[0].skills["cthulhu_mythos"] == 3


def _state_with_character(character: CharacterState):
    reducer = StateReducer()
    state = reducer.initial(session_id="ses", system_id="coc7e")
    return reducer.apply(
        state,
        DomainEvent(
            session_id="ses",
            event_type="CharacterCreated",
            actor_id=character.id,
            payload=character.model_dump(mode="json"),
            trace_id="trc",
        ),
    )
