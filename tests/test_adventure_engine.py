from chatrpg.ir.adventure import AdventureIR, ClueCarrier, ContentUnit, Revelation
from chatrpg.runtime.adventure import AdventureEngine
from chatrpg.runtime.state import StateReducer


def test_adventure_frontier_returns_unlocked_units_and_clues() -> None:
    adventure = AdventureIR(
        adventure_id="adv",
        system_id="coc7e",
        title="Case",
        units=[
            ContentUnit(
                id="u1",
                adventure_id="adv",
                kind="location",
                title="Room",
                summary="A room.",
                visibility="keeper_only",
            )
        ],
        revelations=[Revelation(id="r1", adventure_id="adv", truth_summary="Truth")],
        clues=[ClueCarrier(id="c1", revelation_id="r1", carrier_type="object", unit_id="u1", acquisition="automatic")],
    )
    engine = AdventureEngine()
    reducer = StateReducer()
    state = reducer.initial(session_id="ses", system_id="coc7e", adventure_id="adv")
    state = reducer.apply(state, engine.unlock_unit_event(session_id="ses", unit_id="u1", trace_id="trc"))
    frontier = engine.frontier(adventure=adventure, state=state)
    assert len(frontier.units) == 1
    assert len(frontier.clues) == 1
