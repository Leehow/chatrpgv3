from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState
from chatrpg.runtime.state import StateReducer


def test_reducer_unlocks_frontier_once() -> None:
    reducer = StateReducer()
    state = reducer.initial(session_id="ses", system_id="coc7e")
    event = DomainEvent(
        session_id="ses",
        event_type="FrontierUnlocked",
        payload={"unit_id": "u1"},
        trace_id="trc",
    )
    result = reducer.replay(state, [event, event])
    assert result.unlocked_frontier == ["u1"]


def test_reducer_applies_character_resources() -> None:
    reducer = StateReducer()
    state = reducer.initial(session_id="ses", system_id="coc7e")
    character = CharacterState(id="pc1", name="Investigator", resources={"luck": 40})
    created = DomainEvent(
        session_id="ses",
        event_type="CharacterCreated",
        actor_id="pc1",
        payload=character.model_dump(mode="json"),
        trace_id="trc",
    )
    changed = DomainEvent(
        session_id="ses",
        event_type="CharacterResourceChanged",
        actor_id="pc1",
        payload={"resource_id": "luck", "delta": -5},
        trace_id="trc",
    )
    result = reducer.replay(state, [created, changed])
    assert result.party[0].resources["luck"] == 35
