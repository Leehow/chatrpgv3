import asyncio
from types import SimpleNamespace

from chatrpg.agents.contracts import IntentFrame, NarrationRequest, NarrationResult, PlayerInput
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState
from chatrpg.play import PlayEngine
from chatrpg.retrieval.semantic import SemanticMatchRequest, SemanticMatchResult


class Agent:
    def __init__(self) -> None:
        self.player_input: PlayerInput | None = None
        self.narration_request: NarrationRequest | None = None

    async def resolve_intent(self, player_input: PlayerInput, *, trace_id: str) -> IntentFrame:
        self.player_input = player_input
        return IntentFrame(
            intent="settle observation",
            procedure_id="coc7e.skill_roll",
            actor_id="pc1",
            inputs={"skill_id": "spot_hidden", "reason": "desk search"},
            confidence=1.0,
        )

    async def narrate(self, request: NarrationRequest, *, trace_id: str) -> NarrationResult:
        self.narration_request = request
        return NarrationResult(text="settled")


class EventStore:
    def __init__(self, events: list[DomainEvent]) -> None:
        self.events = list(events)
        self.session = SimpleNamespace(system_id="coc7e", adventure_id=None)

    async def get_session_row(self, *, session_id: str) -> SimpleNamespace:
        return self.session

    async def list_events(self, *, session_id: str) -> list[DomainEvent]:
        return list(self.events)

    async def append_many(self, events: list[DomainEvent]) -> None:
        self.events.extend(events)


class IRStore:
    async def get_adventure(self, *, adventure_id: str):
        return None


class TraceStore:
    async def record_match(self, *, request: SemanticMatchRequest, result: SemanticMatchResult, trace_id: str) -> str:
        return "sem"


class Matcher:
    async def match(self, request: SemanticMatchRequest, *, trace_id: str) -> SemanticMatchResult:
        return SemanticMatchResult(status="no_match")


def test_play_engine_runs_native_procedure_from_intent() -> None:
    async def run_case() -> None:
        agent = Agent()
        store = EventStore(events=[character_created()])
        engine = PlayEngine(
            agent=agent,
            event_store=store,
            ir_store=IRStore(),
            semantic_trace_store=TraceStore(),
            semantic_matcher=Matcher(),
        )
        result = await engine.turn(session_id="ses", message="search the desk", actor_id="pc1")

        assert agent.player_input is not None
        assert agent.player_input.context["party_status"][0]["skills"]["spot_hidden"] == 70
        assert "coc7e.skill.exploration_check" in {skill["id"] for skill in agent.player_input.context["agent_skills"]}
        assert "SkillRollResolved" in [event.event_type for event in result.committed_events]
        assert result.procedure_result is not None
        assert any(step.stage.startswith("AgentLoop[") for step in result.agent_trace)
        assert agent.narration_request is not None
        assert any(fact.get("type") == "procedure_result" for fact in agent.narration_request.visible_facts)
        assert any(fact.get("type") == "agent_trace" for fact in agent.narration_request.visible_facts)

    asyncio.run(run_case())


def character_created() -> DomainEvent:
    return DomainEvent(
        session_id="ses",
        event_type="CharacterCreated",
        actor_id="pc1",
        payload=CharacterState(
            id="pc1",
            name="Investigator",
            owner="player",
            resources={"sanity": 50, "luck": 40},
            traits={"int": 80},
            skills={"spot_hidden": 70},
        ).model_dump(mode="json"),
        trace_id="trc",
    )
