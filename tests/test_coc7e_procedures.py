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


def test_coc7e_opposed_roll_and_chase_round_emit_events() -> None:
    state = _state_with_character(
        CharacterState(id="pc1", name="Investigator", resources={"hp": 10}, traits={"dex": 60}, skills={"dodge": 70})
    )
    runner = Coc7eProcedureRunner(DiceEngine(seed=9))

    opposed = runner.run(
        procedure_id="coc7e.opposed_roll",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={"attacker_target": 70, "defender_target": 40, "reason": "grapple"},
        trace_id="trc",
    )
    chase = runner.run(
        procedure_id="coc7e.chase_round",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={
            "participants": [
                {"id": "pc1", "role": "quarry", "move": 8, "dex": 60},
                {"id": "cultist", "role": "pursuer", "move": 7, "dex": 50},
            ],
            "movement_actor_id": "pc1",
            "skill_id": "dodge",
        },
        trace_id="trc",
    )

    assert opposed.status == "completed"
    assert opposed.events[0].event_type == "OpposedRollResolved"
    assert chase.status == "completed"
    assert chase.events[0].event_type == "ChaseRoundResolved"


def test_coc7e_recovery_and_madness_procedures_update_state() -> None:
    reducer = StateReducer()
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"hp": 4, "sanity": 50},
            skills={"first_aid": 90},
            conditions=["dying", "temporary_insanity"],
        )
    )
    runner = Coc7eProcedureRunner(DiceEngine(seed=2))
    aid = runner.run(
        procedure_id="coc7e.first_aid",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={"target_actor_id": "pc1", "healing": 1, "reason": "bind wounds"},
        trace_id="trc",
    )
    next_state = reducer.replay(state, aid.events)
    madness = runner.run(
        procedure_id="coc7e.bout_of_madness",
        session_id="ses",
        state=next_state,
        actor_id="pc1",
        inputs={"mode": "summary"},
        trace_id="trc",
    )
    final_state = reducer.replay(next_state, madness.events)

    assert aid.status == "completed"
    assert next_state.party[0].resources["hp"] == 5
    assert "dying" not in next_state.party[0].conditions
    assert madness.events[0].event_type == "BoutOfMadnessResolved"
    assert any(condition.startswith("bout_of_madness_") for condition in final_state.party[0].conditions)


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
