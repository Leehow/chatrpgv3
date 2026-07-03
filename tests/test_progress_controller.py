from chatrpg.ir.adventure import AdventureIR, Revelation
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState
from chatrpg.runtime.progress import ProgressController
from chatrpg.runtime.state import StateReducer


def test_progress_requires_character_before_opening() -> None:
    state = StateReducer().initial(session_id="ses", system_id="coc7e")
    snapshot = ProgressController().snapshot(state=state, adventure=None)
    assert snapshot.phase == "character_creation"
    assert snapshot.pressure == "low"


def test_progress_counts_known_revelations() -> None:
    reducer = StateReducer()
    state = reducer.initial(session_id="ses", system_id="coc7e")
    state = reducer.apply(
        state,
        DomainEvent(
            session_id="ses",
            event_type="CharacterCreated",
            actor_id="pc1",
            payload=CharacterState(id="pc1", name="Investigator").model_dump(mode="json"),
            trace_id="trc",
        ),
    )
    state = reducer.apply(
        state,
        DomainEvent(
            session_id="ses",
            event_type="FactLearned",
            payload={"id": "r1", "known_by": "player_group", "confidence": "confirmed", "source_event_id": "c1"},
            trace_id="trc",
        ),
    )
    adventure = AdventureIR(
        adventure_id="adv",
        system_id="coc7e",
        title="Case",
        revelations=[
            Revelation(id="r1", adventure_id="adv", truth_summary="One"),
            Revelation(id="r2", adventure_id="adv", truth_summary="Two"),
        ],
    )

    snapshot = ProgressController().snapshot(state=state, adventure=adventure)

    assert snapshot.phase == "investigation"
    assert snapshot.pressure == "medium"
    assert snapshot.completion_ratio == 0.5
    assert snapshot.unresolved_revelation_ids == ["r2"]
