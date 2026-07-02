from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.agents.contracts import IntentFrame, NarrationRequest, NarrationResult, PlayerInput
from chatrpg.agents.main_agent import PiMainAgent
from chatrpg.core.ids import new_id
from chatrpg.db.repositories import PostgresEventStore, PostgresIRStore, PostgresSemanticTraceStore
from chatrpg.ir.adventure import AdventureIR, HandoutAsset
from chatrpg.ir.events import DomainEvent
from chatrpg.retrieval.traced import TracedSemanticMatcher
from chatrpg.runtime.adventure import AdventureEngine
from chatrpg.runtime.clues import ClueAcquisitionDecision, ClueAcquisitionEngine
from chatrpg.runtime.handouts import HandoutEngine
from chatrpg.runtime.state import StateReducer


class PlayTurnResult(BaseModel):
    trace_id: str
    intent: IntentFrame
    narration: NarrationResult
    committed_events: list[DomainEvent] = Field(default_factory=list)
    clue_decision: dict[str, object] | None = None


class PlayEngine:
    def __init__(
        self,
        *,
        agent: PiMainAgent,
        event_store: PostgresEventStore,
        ir_store: PostgresIRStore,
        semantic_trace_store: PostgresSemanticTraceStore,
        semantic_matcher: object,
    ) -> None:
        self._agent = agent
        self._event_store = event_store
        self._ir_store = ir_store
        self._semantic_trace_store = semantic_trace_store
        self._semantic_matcher = semantic_matcher
        self._adventures = AdventureEngine()
        self._handouts = HandoutEngine()
        self._reducer = StateReducer()

    async def turn(self, *, session_id: str, message: str, actor_id: str | None = None) -> PlayTurnResult:
        trace_id = new_id("trc")
        intent = await self._agent.resolve_intent(
            PlayerInput(session_id=session_id, actor_id=actor_id, message=message),
            trace_id=trace_id,
        )
        session_row = await self._event_store.get_session_row(session_id=session_id)
        if session_row is None:
            raise LookupError(f"session not found: {session_id}")
        prior_events = await self._event_store.list_events(session_id=session_id)
        state = self._reducer.replay(
            self._reducer.initial(
                session_id=session_id,
                system_id=session_row.system_id,
                adventure_id=session_row.adventure_id,
            ),
            prior_events,
        )
        adventure = await self._load_adventure(session_row.adventure_id)
        committed_events: list[DomainEvent] = []
        clue_decision: ClueAcquisitionDecision | None = None
        if adventure is not None:
            frontier = self._adventures.frontier(adventure=adventure, state=state)
            traced = TracedSemanticMatcher(
                matcher=self._semantic_matcher,
                trace_store=self._semantic_trace_store,
            )
            clue_decision = await ClueAcquisitionEngine(traced).select_clue(
                player_action=message,
                available_clues=list(frontier.clues),
                trace_id=trace_id,
            )
            if clue_decision.clue is not None:
                committed_events.extend(
                    self._adventures.clue_found_events(
                        session_id=session_id,
                        clue=clue_decision.clue,
                        trace_id=trace_id,
                    )
                )
                committed_events.extend(
                    self._reveal_linked_handouts(
                        session_id=session_id,
                        adventure=adventure,
                        reveal_targets=[clue_decision.clue.id, clue_decision.clue.revelation_id],
                        trace_id=trace_id,
                    )
                )
        if committed_events:
            await self._event_store.append_many(committed_events)
        narration = await self._agent.narrate(
            NarrationRequest(
                session_id=session_id,
                committed_events=[event.model_dump(mode="json") for event in [*prior_events, *committed_events]],
                visible_facts=[intent.model_dump(mode="json")],
            ),
            trace_id=trace_id,
        )
        return PlayTurnResult(
            trace_id=trace_id,
            intent=intent,
            narration=narration,
            committed_events=committed_events,
            clue_decision=None if clue_decision is None else clue_decision.__dict__,
        )

    async def _load_adventure(self, adventure_id: str | None) -> AdventureIR | None:
        if adventure_id is None:
            return None
        return await self._ir_store.get_adventure(adventure_id=adventure_id)

    def _reveal_linked_handouts(
        self,
        *,
        session_id: str,
        adventure: AdventureIR,
        reveal_targets: list[str],
        trace_id: str,
    ) -> list[DomainEvent]:
        revealed: list[DomainEvent] = []
        target_set = set(reveal_targets)
        for handout in adventure.handouts:
            if self._handout_reveals_any(handout, target_set):
                revealed.append(self._handouts.reveal_event(session_id=session_id, handout=handout, trace_id=trace_id))
        return revealed

    @staticmethod
    def _handout_reveals_any(handout: HandoutAsset, reveal_targets: set[str]) -> bool:
        return bool(set(handout.reveals).intersection(reveal_targets))
