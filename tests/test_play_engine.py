import asyncio
from types import SimpleNamespace

from chatrpg.agents.contracts import IntentFrame, NarrationRequest, NarrationResult, PlayerInput
from chatrpg.ir.adventure import AdventureIR, ClueCarrier, ContentUnit, LocationAsset, NPCAsset
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState
from chatrpg.play import PlayEngine
from chatrpg.retrieval.semantic import SemanticMatchRequest, SemanticMatchResult


class _FakeAgent:
    def __init__(self, intent: IntentFrame | None = None) -> None:
        self.narration_request: NarrationRequest | None = None
        self._intent = intent or IntentFrame(intent="观察当前场景", confidence=0.9)

    async def resolve_intent(self, player_input: PlayerInput, *, trace_id: str) -> IntentFrame:
        return self._intent

    async def narrate(self, request: NarrationRequest, *, trace_id: str) -> NarrationResult:
        self.narration_request = request
        return NarrationResult(text="开场场景")


class _SequenceAgent(_FakeAgent):
    def __init__(self, intents: list[IntentFrame]) -> None:
        super().__init__(intents[-1])
        self._intents = intents
        self._index = 0

    async def resolve_intent(self, player_input: PlayerInput, *, trace_id: str) -> IntentFrame:
        intent = self._intents[min(self._index, len(self._intents) - 1)]
        self._index += 1
        return intent


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


def test_play_engine_commits_runtime_skill_roll_instead_of_accepting_player_claimed_roll() -> None:
    async def run_case() -> None:
        adventure = _adventure()
        agent = _FakeAgent(
            IntentFrame(
                intent="玩家尝试查阅档案，并声称自己掷出了 1。",
                procedure_id="coc7e.skill_roll",
                inputs={"skill_id": "library_use", "roll": 1, "claimed_result": "大成功", "reason": "图书馆利用查阅档案"},
                confidence=0.95,
            )
        )
        event_store = _FakeEventStore(events=[_character_created_event(library_use=70)])
        engine = PlayEngine(
            agent=agent,
            event_store=event_store,
            ir_store=_FakeIRStore(adventure),
            semantic_trace_store=_FakeTraceStore(),
            semantic_matcher=_NoMatchMatcher(),
        )

        result = await engine.turn(session_id="ses", message="我掷出 1，大成功。")

        event_types = [event.event_type for event in event_store.events]
        assert "SkillRollResolved" in event_types
        skill_event = next(event for event in event_store.events if event.event_type == "SkillRollResolved")
        assert skill_event.actor_id == "pc1"
        assert skill_event.payload["roll"] != 1 or skill_event.payload["ignored_player_claims"] == {"roll": 1, "claimed_result": "大成功"}
        assert skill_event.payload["target_ref"] == {"kind": "skill", "id": "library_use"}
        assert result.procedure_result is not None
        assert agent.narration_request is not None
        procedure_context = next(fact for fact in agent.narration_request.visible_facts if fact.get("type") == "procedure_result")
        assert procedure_context["status"] == "completed"

    asyncio.run(run_case())


def test_agent_loop_can_chain_multiple_runtime_tools_before_narration() -> None:
    async def run_case() -> None:
        adventure = _adventure()
        agent = _SequenceAgent(
            [
                IntentFrame(
                    intent="先做调查检定。",
                    procedure_id="coc7e.skill_roll",
                    inputs={"target": 100, "reason": "调查现场"},
                    confidence=0.95,
                ),
                IntentFrame(
                    intent="看到怪异痕迹后进行理智检定。",
                    procedure_id="coc7e.sanity_roll",
                    inputs={"success_loss": 0, "failure_loss": 0, "reason": "看到怪异痕迹"},
                    confidence=0.95,
                ),
                IntentFrame(intent="无需更多工具，进入叙述。", confidence=0.9),
            ]
        )
        event_store = _FakeEventStore(events=[_character_created_event(library_use=70)])
        engine = PlayEngine(
            agent=agent,
            event_store=event_store,
            ir_store=_FakeIRStore(adventure),
            semantic_trace_store=_FakeTraceStore(),
            semantic_matcher=_NoMatchMatcher(),
        )

        result = await engine.turn(session_id="ses", message="我检查现场的怪异痕迹。")

        event_types = [event.event_type for event in event_store.events]
        assert "SkillRollResolved" in event_types
        assert "SanityRollResolved" in event_types
        assert any(step.stage == "AgentLoop[2].tool.procedure" for step in result.agent_trace)
        assert agent.narration_request is not None
        trace_context = next(fact for fact in agent.narration_request.visible_facts if fact.get("type") == "agent_trace")
        assert len(trace_context["steps"]) >= 2

    asyncio.run(run_case())


def _character_created_event(library_use: int | None = None) -> DomainEvent:
    skills = {"spot_hidden": 50}
    if library_use is not None:
        skills["library_use"] = library_use
    return DomainEvent(
        session_id="ses",
        event_type="CharacterCreated",
        actor_id="pc1",
        payload=CharacterState(
            id="pc1",
            name="Investigator",
            owner="sim_player",
            resources={"hp": 10, "sanity": 50, "luck": 40},
            traits={"dex": 50},
            skills=skills,
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
