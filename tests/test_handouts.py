from chatrpg.ir.adventure import AdventureIR, HandoutAsset
from chatrpg.runtime.handouts import HandoutEngine
from chatrpg.runtime.state import StateReducer


def test_handout_reveal_event_updates_visible_handouts() -> None:
    adventure = AdventureIR(
        adventure_id="adv",
        system_id="coc7e",
        title="Case",
        handouts=[HandoutAsset(id="h1", adventure_id="adv", title="Note", summary="A note.")],
    )
    engine = HandoutEngine()
    reducer = StateReducer()
    state = reducer.initial(session_id="ses", system_id="coc7e", adventure_id="adv")
    event = engine.reveal_event(session_id="ses", handout=adventure.handouts[0], trace_id="trc")
    state = reducer.apply(state, event)
    assert [handout.id for handout in engine.visible_handouts(adventure=adventure, state=state)] == ["h1"]
