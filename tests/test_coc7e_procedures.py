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


def test_coc7e_luck_spend_uses_pending_failed_roll() -> None:
    reducer = StateReducer()
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"sanity": 50, "luck": 70},
            skills={"library_use": 70},
        )
    )
    failed_roll = DomainEvent(
        session_id="ses",
        event_type="SkillRollResolved",
        actor_id="pc1",
        payload={
            "roll": 94,
            "target": 70,
            "difficulty": "regular",
            "level": "failure",
            "passed": False,
            "can_push": True,
            "can_spend_luck": True,
            "luck_to_success": 24,
            "target_ref": {"kind": "skill", "id": "library_use"},
        },
        trace_id="trc",
    )
    state = reducer.apply(state, failed_roll)

    result = Coc7eProcedureRunner(DiceEngine(seed=1)).run(
        procedure_id="coc7e.luck_spend",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={},
        trace_id="trc",
    )
    next_state = reducer.replay(state, result.events)

    assert result.status == "completed"
    assert result.events[0].event_type == "LuckSpent"
    assert result.events[0].payload["source_event_id"] == failed_roll.id
    assert result.events[0].payload["luck_spent"] == 24
    assert result.events[0].payload["passed"] is True
    assert next_state.party[0].resources["luck"] == 46
    assert next_state.pending_decisions == []


def test_coc7e_luck_decline_clears_pending_failed_roll() -> None:
    reducer = StateReducer()
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"sanity": 50, "luck": 70},
            skills={"library_use": 70},
        )
    )
    failed_roll = DomainEvent(
        session_id="ses",
        event_type="SkillRollResolved",
        actor_id="pc1",
        payload={
            "roll": 94,
            "target": 70,
            "difficulty": "regular",
            "level": "failure",
            "passed": False,
            "can_push": True,
            "can_spend_luck": True,
            "luck_to_success": 24,
            "target_ref": {"kind": "skill", "id": "library_use"},
        },
        trace_id="trc",
    )
    state = reducer.apply(state, failed_roll)

    result = Coc7eProcedureRunner(DiceEngine(seed=1)).run(
        procedure_id="coc7e.luck_decline",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={},
        trace_id="trc",
    )
    next_state = reducer.replay(state, result.events)

    assert result.status == "completed"
    assert result.events[0].event_type == "LuckSpendDeclined"
    assert result.events[0].payload["source_event_id"] == failed_roll.id
    assert next_state.party[0].resources["luck"] == 70
    assert next_state.pending_decisions == []


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


def test_coc7e_sanity_procedure_accepts_dice_notation_strings() -> None:
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"sanity": 1, "luck": 40},
            traits={"int": 80},
            skills={"cthulhu_mythos": 0},
        )
    )
    result = Coc7eProcedureRunner(DiceEngine(seed=1)).run(
        procedure_id="coc7e.sanity_roll",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={"success_loss": 0, "failure_loss": "1D6", "reason": "mythos shock"},
        trace_id="trc",
    )

    assert result.status == "completed"
    assert result.events[0].event_type == "SanityRollResolved"
    assert result.events[0].payload["loss_roll"]["notation"] == "1D6"


def test_coc7e_sanity_procedure_accepts_numeric_loss_strings() -> None:
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"sanity": 1, "luck": 40},
            traits={"int": 80},
            skills={"cthulhu_mythos": 0},
        )
    )
    result = Coc7eProcedureRunner(DiceEngine(seed=1)).run(
        procedure_id="coc7e.sanity_roll",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={"success_loss": "0", "failure_loss": "3", "reason": "mythos shock"},
        trace_id="trc",
    )

    assert result.status == "completed"
    assert result.events[0].payload["sanity_lost"] == 3


def test_coc7e_combat_attack_accepts_damage_dice_notation_string() -> None:
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"hp": 12, "sanity": 50, "luck": 40},
            skills={"fighting_brawl": 90},
        )
    )
    result = Coc7eProcedureRunner(DiceEngine(seed=31)).run(
        procedure_id="coc7e.combat_attack",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={
            "skill_id": "fighting_brawl",
            "target_hp": 8,
            "damage": "1D6",
            "reason": "combat smoke test",
        },
        trace_id="trc",
    )

    assert result.status == "completed"
    assert result.events[0].event_type == "AttackResolved"


def test_coc7e_combat_attack_with_target_hp_does_not_default_defender_to_actor() -> None:
    reducer = StateReducer()
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"hp": 12, "sanity": 50, "luck": 40},
            skills={"fighting_brawl": 90},
        )
    )
    result = Coc7eProcedureRunner(DiceEngine(seed=31)).run(
        procedure_id="coc7e.combat_attack",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={
            "skill_id": "fighting_brawl",
            "target_hp": 8,
            "damage": "1D6",
            "reason": "combat smoke test",
        },
        trace_id="trc",
    )
    next_state = reducer.replay(state, result.events)

    assert result.status == "completed"
    assert [event.event_type for event in result.events] == ["AttackResolved"]
    assert result.events[0].payload["target_hp_before"] == 8
    assert next_state.party[0].resources["hp"] == 12


def test_coc7e_combat_attack_without_target_hp_still_resolves_attack_only() -> None:
    reducer = StateReducer()
    state = _state_with_character(
        CharacterState(
            id="pc1",
            name="Investigator",
            resources={"hp": 12, "sanity": 50, "luck": 40},
            skills={"fighting_brawl": 90},
        )
    )
    result = Coc7eProcedureRunner(DiceEngine(seed=31)).run(
        procedure_id="coc7e.combat_attack",
        session_id="ses",
        state=state,
        actor_id="pc1",
        inputs={
            "skill_id": "fighting_brawl",
            "target": "npc_mr_knott",
            "damage": "1D3+0",
            "reason": "attack an untracked NPC",
        },
        trace_id="trc",
    )
    next_state = reducer.replay(state, result.events)

    assert result.status == "completed"
    assert [event.event_type for event in result.events] == ["AttackResolved"]
    assert result.events[0].payload["target_hp_known"] is False
    assert result.events[0].payload["attack"]["hit"] is True
    assert next_state.party[0].resources["hp"] == 12


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
