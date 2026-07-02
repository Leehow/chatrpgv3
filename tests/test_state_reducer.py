from chatrpg.ir.events import DomainEvent
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
