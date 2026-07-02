import asyncio
from types import SimpleNamespace

from chatrpg.agents.contracts import IntentFrame, NarrationRequest, NarrationResult, PlayerInput
from chatrpg.ir.adventure import AdventureIR, ClueCarrier, ContentUnit, LocationAsset, NPCAsset
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState
from chatrpg.play import PlayEngine
from chatrpg.retrieval.semantic import SemanticMatchRequest, SemanticMatchResult


class _FakeAgent:
    def __init__(self) -> None:
        self.narration_request: NarrationRequest | None = None

    async def resolve_intent(self, player_input: PlayerInput, *, trace_id: str) -> IntentFrame:
        return IntentFrame(intent="观察当前场景", confidence=0.9)

    async def narrate(self, request: NarrationRequest, *, trace_id: str) -> NarrationResult:
        self.narration_request = request
        return NarrationResult(text="开场场景")


class _FakeEventStore:
    def __init__(self, events: list[DomainEvent] | None = None) -> None:
        self.events = list(events or [])
        self.session = SimpleNamespace(system_id="coc7e", adventure_id="adv")

    async def get_session_row(self, *, session_id: str) -> SimpleNamespace:
        return self.session

    async def list_events(self, *, session_id: str) -> list:
        return list(self.events)

    async def append_many(self, events: list) -> None:
        self.events.extend(events)


class _FakeIRStore:
    def __init__(self, adventure: AdventureIR) -> None:
        self._adventure = adventure

    async def get_adventure(self, *, adventure_id: str) -> AdventureIR:
        return self._adventure


class _FakeTraceStore:
    async def record_match(self, *, request: SemanticMatchRequest, result: SemanticMatchResult, trace_id: str) -> str:
        return "sem_fake"


class _NoMatchMatcher:
    async def match(self, request: SemanticMatchRequest, *, trace_id: str) -> SemanticMatchResult:
        return SemanticMatchResult(status="no_match")


def test_first_turn_requires_character_before_opening_frontier() -> None:
    async def run_case() -> None:
        adventure = _adventure()
        agent = _FakeAgent()
        event_store = _FakeEventStore()
        engine = PlayEngine(
            agent=agent,
            event_store=event_store,
            ir_store=_FakeIRStore(adventure),
            semantic_trace_store=_FakeTraceStore(),
            semantic_matcher=_NoMatchMatcher(),
        )

        await engine.turn(session_id="ses", message="我观察当前场景")

        assert [event.event_type for event in event_store.events] == ["WorkflowPhaseEntered"]
        assert event_store.events[0].payload == {"phase_id": "coc7e.character_creation"}
        assert agent.narration_request is not None
        workflow = next(fact for fact in agent.narration_request.visible_facts if fact.get("type") == "workflow_state")
        assert workflow["phase_id"] == "coc7e.character_creation"
        assert workflow["requires_character_creation"] is True
        assert not any(fact.get("type") == "adventure_frontier" for fact in agent.narration_request.visible_facts)

    asyncio.run(run_case())


def test_first_turn_with_character_bootstraps_player_visible_opening_unit_into_narration_context() -> None:
    async def run_case() -> None:
        adventure = _adventure()
        agent = _FakeAgent()
        event_store = _FakeEventStore(events=[_character_created_event()])
        engine = PlayEngine(
            agent=agent,
            event_store=event_store,
            ir_store=_FakeIRStore(adventure),
            semantic_trace_store=_FakeTraceStore(),
            semantic_matcher=_NoMatchMatcher(),
        )

        await engine.turn(session_id="ses", message="我观察当前场景")

        assert [event.event_type for event in event_store.events] == [
            "CharacterCreated",
            "WorkflowPhaseEntered",
            "WorkflowPhaseCompleted",
            "WorkflowPhaseEntered",
            "FrontierUnlocked",
        ]
        assert event_store.events[-1].payload == {"unit_id": "unit_setup"}
        assert agent.narration_request is not None
        workflow_context = next(fact for fact in agent.narration_request.visible_facts if fact.get("type") == "workflow_state")
        assert workflow_context["phase_id"] == "coc7e.investigation"
        party_context = next(fact for fact in agent.narration_request.visible_facts if fact.get("type") == "party_status")
        assert party_context["characters"][0]["name"] == "Investigator"
        adventure_context = next(
            fact for fact in agent.narration_request.visible_facts if fact.get("type") == "adventure_frontier"
        )
        assert adventure_context["units"][0]["id"] == "unit_setup"
        assert adventure_context["locations"][0]["name"] == "Boston"
        assert adventure_context["npcs"][0]["name"] == "Mr. Knott"

    asyncio.run(run_case())


def _character_created_event() -> DomainEvent:
    return DomainEvent(
        session_id="ses",
        event_type="CharacterCreated",
        actor_id="pc1",
        payload=CharacterState(
            id="pc1",
            name="Investigator",
            owner="sim_player",
            resources={"hp": 10, "sanity": 50, "luck": 40},
            skills={"spot_hidden": 50},
        ).model_dump(mode="json"),
        trace_id="trc",
    )


def _adventure() -> AdventureIR:
    return AdventureIR(
        adventure_id="adv",
        system_id="coc7e",
        title="The Haunting",
        units=[
            ContentUnit(
                id="unit_setup",
                adventure_id="adv",
                kind="briefing",
                title="The Job from Mr. Knott",
                summary="The investigators are hired in 1920s Boston.",
                visibility="player_visible",
            )
        ],
        clues=[
            ClueCarrier(
                id="clue_setup",
                revelation_id="rev_house",
                carrier_type="briefing",
                unit_id="unit_setup",
                acquisition="automatic briefing",
                visibility="player_visible",
            )
        ],
        npcs=[
            NPCAsset(
                id="npc_knott",
                adventure_id="adv",
                name="Mr. Knott",
                summary="The landlord who hires the investigators.",
                public_profile="Anxious property owner.",
                unit_ids=["unit_setup"],
            )
        ],
        locations=[
            LocationAsset(
                id="loc_boston",
                adventure_id="adv",
                name="Boston",
                summary="Default 1920 setting.",
                unit_ids=["unit_setup"],
            )
        ],
    )
