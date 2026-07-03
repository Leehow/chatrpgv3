import asyncio
from types import SimpleNamespace

from chatrpg.agents.contracts import IntentFrame, NarrationRequest, NarrationResult, PlayerInput
from chatrpg.ir.adventure import AdventureIR, ContentUnit, NPCAsset
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.mechanics import EntityRef, MechanicAffordance
from chatrpg.ir.state import CharacterState
from chatrpg.play import PlayEngine
from chatrpg.retrieval.semantic import SemanticChoice, SemanticMatchRequest, SemanticMatchResult
from chatrpg.runtime.state import StateReducer


class PassiveAgent:
    def __init__(self) -> None:
        self.narration_request: NarrationRequest | None = None

    async def resolve_intent(self, player_input: PlayerInput, *, trace_id: str) -> IntentFrame:
        return IntentFrame(intent="玩家声明一个会改变当前虚构情境的行动。", confidence=0.9)

    async def narrate(self, request: NarrationRequest, *, trace_id: str) -> NarrationResult:
        self.narration_request = request
        return NarrationResult(text="已根据 Runtime 事件叙述。")


class MechanicMatcher:
    def __init__(self, trigger_kind: str) -> None:
        self.trigger_kind = trigger_kind
        self.requests: list[SemanticMatchRequest] = []

    async def match(self, request: SemanticMatchRequest, *, trace_id: str) -> SemanticMatchResult:
        self.requests.append(request)
        if request.task != "mechanic.trigger":
            return SemanticMatchResult(status="no_match")
        for candidate in request.candidates:
            if candidate.metadata.get("trigger_kind") == self.trigger_kind:
                return SemanticMatchResult(
                    status="matched",
                    choices=[SemanticChoice(candidate_id=candidate.id, confidence=0.96, rationale="语义上触发该机制。")],
                )
        return SemanticMatchResult(status="no_match")


class EventStore:
    def __init__(self, events: list[DomainEvent]) -> None:
        self.events = list(events)
        self.session = SimpleNamespace(system_id="coc7e", adventure_id="adv")

    async def get_session_row(self, *, session_id: str) -> SimpleNamespace:
        return self.session

    async def list_events(self, *, session_id: str) -> list[DomainEvent]:
        return list(self.events)

    async def append_many(self, events: list[DomainEvent]) -> None:
        self.events.extend(events)


class IRStore:
    def __init__(self, adventure: AdventureIR) -> None:
        self.adventure = adventure

    async def get_adventure(self, *, adventure_id: str) -> AdventureIR:
        return self.adventure


class TraceStore:
    async def record_match(self, *, request: SemanticMatchRequest, result: SemanticMatchResult, trace_id: str) -> str:
        return "sem_fake"


def test_semantic_mechanic_judge_synthesizes_npc_and_starts_combat_scene() -> None:
    async def run_case() -> None:
        agent = PassiveAgent()
        matcher = MechanicMatcher("aggression")
        store = EventStore(events=[_character_created_event()])
        engine = PlayEngine(
            agent=agent,
            event_store=store,
            ir_store=IRStore(_adventure_with_patron()),
            semantic_trace_store=TraceStore(),
            semantic_matcher=matcher,
        )

        result = await engine.turn(session_id="ses", message="我抄起烟灰缸砸向给任务的NPC。", actor_id="sim_player")

        event_types = [event.event_type for event in result.committed_events]
        assert "RuntimeActorCreated" in event_types
        assert "AttackResolved" in event_types
        assert "CombatStarted" in event_types
        assert any(step.stage.endswith("mechanic_judge") for step in result.agent_trace)
        assert any(request.task == "mechanic.trigger" for request in matcher.requests)
        created = next(event for event in result.committed_events if event.event_type == "RuntimeActorCreated")
        assert created.payload["provenance"]["kind"] == "synthesized"
        replayed = StateReducer().replay(
            StateReducer().initial(session_id="ses", system_id="coc7e", adventure_id="adv"),
            [*[_character_created_event()], *result.committed_events],
        )
        assert replayed.runtime_actors
        assert replayed.active_combats
        combat = replayed.active_combats[0]
        assert "pc1" in combat["participants"]
        assert created.payload["actor"]["id"] in combat["participants"]

    asyncio.run(run_case())


def test_semantic_mechanic_judge_triggers_sanity_roll_from_affordance() -> None:
    async def run_case() -> None:
        agent = PassiveAgent()
        matcher = MechanicMatcher("horror_exposure")
        store = EventStore(events=[_character_created_event()])
        engine = PlayEngine(
            agent=agent,
            event_store=store,
            ir_store=IRStore(_adventure_with_horror_affordance()),
            semantic_trace_store=TraceStore(),
            semantic_matcher=matcher,
        )

        result = await engine.turn(session_id="ses", message="我看清了墙上那具扭曲尸体。", actor_id="sim_player")

        event_types = [event.event_type for event in result.committed_events]
        assert "SanityRollResolved" in event_types
        assert any(event.event_type == "CharacterResourceChanged" for event in result.committed_events) or any(
            event.payload.get("sanity_lost") == 0 for event in result.committed_events if event.event_type == "SanityRollResolved"
        )
        assert agent.narration_request is not None
        trace_context = next(fact for fact in agent.narration_request.visible_facts if fact.get("type") == "agent_trace")
        assert any(step["stage"].endswith("mechanic_judge") for step in trace_context["steps"])

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
            resources={"hp": 12, "hp_max": 12, "sanity": 60, "luck": 50},
            traits={"dex": 50, "int": 70},
            skills={"fighting_brawl": 55, "dodge": 25, "spot_hidden": 60},
        ).model_dump(mode="json"),
        trace_id="trc",
    )


def _adventure_with_patron() -> AdventureIR:
    return AdventureIR(
        adventure_id="adv",
        system_id="coc7e",
        title="Test Haunting",
        units=[
            ContentUnit(
                id="unit_setup",
                adventure_id="adv",
                kind="briefing",
                title="Briefing",
                summary="A patron gives the job.",
                visibility="player_visible",
            )
        ],
        npcs=[
            NPCAsset(
                id="npc_knott",
                adventure_id="adv",
                name="Mr. Knott",
                summary="The patron who gives the job.",
                public_profile="An anxious landlord.",
                unit_ids=["unit_setup"],
            )
        ],
    )


def _adventure_with_horror_affordance() -> AdventureIR:
    return AdventureIR(
        adventure_id="adv",
        system_id="coc7e",
        title="Test Horror",
        units=[
            ContentUnit(
                id="unit_room",
                adventure_id="adv",
                kind="scene",
                title="Room",
                summary="A room with an awful sight.",
                visibility="player_visible",
            )
        ],
        affordances=[
            MechanicAffordance(
                id="aff_horror_body",
                trigger_kind="horror_exposure",
                subject_ref=EntityRef(kind="stimulus", id="body_on_wall", label="扭曲尸体"),
                trigger_description="An investigator clearly sees, understands, or closely examines a sanity-threatening corpse or unnatural body horror.",
                procedure_candidates=["coc7e.sanity_roll"],
                default_inputs={"success_loss": 0, "failure_loss": {"count": 1, "sides": 4, "modifier": 0}, "reason": "看到扭曲尸体"},
                parameter_requirements=[],
                priority=80,
            )
        ],
    )
