from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chatrpg.agents.contracts import AgentTraceStep, IntentFrame, PlayerInput
from chatrpg.agents.main_agent import PiMainAgent
from chatrpg.ir.adventure import AdventureIR, ClueCarrier, HandoutAsset
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState
from chatrpg.ir.workflow import WorkflowSpec
from chatrpg.play.context import build_intent_context, procedure_passed
from chatrpg.retrieval.traced import TracedSemanticMatcher
from chatrpg.runtime.adventure import AdventureEngine, AdventureFrontier
from chatrpg.runtime.clues import ClueAcquisitionDecision, ClueAcquisitionEngine
from chatrpg.runtime.combat import CombatSceneManager
from chatrpg.runtime.handouts import HandoutEngine
from chatrpg.runtime.mechanics import MechanicTriggerJudge, ParameterResolver, action_frame_from_intent
from chatrpg.runtime.scene import SceneFrameBuilder
from chatrpg.runtime.state import StateReducer
from chatrpg.runtime.workflow import WorkflowEngine
from chatrpg.systems.coc7e.procedures import Coc7eProcedureRunner, ProcedureExecutionResult


@dataclass
class AgentLoopRunRequest:
    session_id: str
    system_id: str
    player_message: str
    trace_id: str
    actor_id: str | None
    state: SessionState
    adventure: AdventureIR | None
    frontier: AdventureFrontier | None
    workflow: WorkflowSpec | None
    can_advance_adventure: bool
    max_steps: int = 6
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentLoopRunResult:
    intent: IntentFrame
    state: SessionState
    frontier: AdventureFrontier | None
    committed_events: list[DomainEvent] = field(default_factory=list)
    clue_decision: ClueAcquisitionDecision | None = None
    procedure_result: ProcedureExecutionResult | None = None
    agent_trace: list[AgentTraceStep] = field(default_factory=list)
    stop_reason: str = "completed"


class AgentLoopEngine:
    def __init__(
        self,
        *,
        agent: PiMainAgent,
        semantic_matcher: object,
        semantic_trace_store: object,
        adventure_engine: AdventureEngine | None = None,
        handout_engine: HandoutEngine | None = None,
        reducer: StateReducer | None = None,
        workflow_engine: WorkflowEngine | None = None,
    ) -> None:
        self._agent = agent
        self._semantic_matcher = semantic_matcher
        self._semantic_trace_store = semantic_trace_store
        self._adventures = adventure_engine or AdventureEngine()
        self._handouts = handout_engine or HandoutEngine()
        self._reducer = reducer or StateReducer()
        self._workflow = workflow_engine or WorkflowEngine(self._reducer)
        self._scene_builder = SceneFrameBuilder()
        self._parameter_resolver = ParameterResolver()
        self._combat_scenes = CombatSceneManager()

    async def run(self, request: AgentLoopRunRequest) -> AgentLoopRunResult:
        state = request.state
        frontier = request.frontier
        committed_events: list[DomainEvent] = []
        trace: list[AgentTraceStep] = []
        executed_tool_keys: set[str] = set()
        history: list[dict[str, object]] = []
        intent = IntentFrame(intent="未解析玩家行动", confidence=0.0)
        procedure_result: ProcedureExecutionResult | None = None
        clue_decision: ClueAcquisitionDecision | None = None
        stop_reason = "max_steps"

        for step_index in range(1, request.max_steps + 1):
            phase = None if request.workflow is None else self._workflow.current_phase(state=state, workflow=request.workflow)
            scene = self._scene_builder.build(
                state=state,
                adventure=request.adventure,
                frontier=frontier,
                recent_event_types=[item.get("event_type", "") for item in history if isinstance(item.get("event_type"), str)],
            )
            context = build_intent_context(
                system_id=request.system_id,
                phase=phase,
                state=state,
                adventure=request.adventure,
                frontier=frontier,
            )
            context["scene_frame"] = scene.model_dump(mode="json")
            context["agent_loop"] = {
                "step_index": step_index,
                "max_steps": request.max_steps,
                "history": history,
                "policy": {
                    "runtime_is_dice_authority": True,
                    "mechanic_triggers_use_semantic_matching": True,
                    "stop_when_no_more_runtime_tool_is_needed": True,
                },
            }
            self._append_trace(
                trace,
                stage=f"AgentLoop[{step_index}].observe",
                summary="构造本轮观察：玩家行动、场景、可触发机制、状态和可用工具。",
                data={
                    "system_id": request.system_id,
                    "party_size": len(state.party),
                    "runtime_actor_count": len(state.runtime_actors),
                    "active_combat_count": len(state.active_combats),
                    "affordance_count": len(scene.active_affordances),
                    "loop_history_count": len(history),
                },
            )
            raw_intent = await self._agent.resolve_intent(
                PlayerInput(
                    session_id=request.session_id,
                    actor_id=request.actor_id,
                    message=request.player_message,
                    context=context,
                ),
                trace_id=request.trace_id,
            )
            intent = self._intent_with_bound_skill_call(raw_intent)
            self._append_trace(
                trace,
                stage=f"AgentLoop[{step_index}].decide",
                summary="GM Agent 选择下一步：调用 Runtime 工具、等待澄清或进入机制触发裁定。",
                data={
                    "intent": intent.intent,
                    "procedure_id": intent.procedure_id,
                    "skill_calls": [call.model_dump(mode="json") for call in intent.skill_calls],
                    "needs_clarification": intent.needs_clarification,
                },
            )
            if intent.needs_clarification:
                stop_reason = "needs_clarification"
                break

            if intent.procedure_id is None:
                action = action_frame_from_intent(message=request.player_message, actor_id=request.actor_id, intent=intent)
                plan = await MechanicTriggerJudge(self._semantic_matcher).judge(
                    action=action,
                    scene=scene,
                    trace_id=request.trace_id,
                )
                self._append_trace(
                    trace,
                    stage=f"AgentLoop[{step_index}].mechanic_judge",
                    summary="使用语义匹配判断当前虚构情境是否触发规则机制。",
                    data=plan.model_dump(mode="json"),
                )
                if plan.status == "planned" and plan.ordered_steps:
                    resolved = self._parameter_resolver.resolve(
                        session_id=request.session_id,
                        state=state,
                        plan=plan,
                        scene=scene,
                        actor_id=request.actor_id,
                        trace_id=request.trace_id,
                    )
                    if resolved.pre_events:
                        committed_events.extend(resolved.pre_events)
                        state = self._reducer.replay(state, resolved.pre_events)
                        self._append_trace(
                            trace,
                            stage=f"AgentLoop[{step_index}].tool.asset_resolution",
                            summary="为机制计划补齐缺失参数并创建可追踪临时资产。",
                            data={"event_types": [event.event_type for event in resolved.pre_events]},
                        )
                    procedure_result = self._run_mechanic_steps(
                        request=request,
                        state=state,
                        steps=resolved.steps,
                        trace=trace,
                        step_index=step_index,
                    )
                    if procedure_result is not None and procedure_result.events:
                        post_events = self._post_process_procedure_events(
                            session_id=request.session_id,
                            state=state,
                            procedure_result=procedure_result,
                            trace_id=request.trace_id,
                        )
                        all_events = [*procedure_result.events, *post_events]
                        committed_events.extend(all_events)
                        state = self._reducer.replay(state, all_events)
                    stop_reason = "mechanic_plan_completed"
                    break
                clue_decision, events, frontier = await self._resolve_clue_tool(
                    request=request,
                    state=state,
                    frontier=frontier,
                    procedure_result=procedure_result,
                )
                if events:
                    committed_events.extend(events)
                    state = self._reducer.replay(state, events)
                    frontier = self._refresh_frontier(request.adventure, state, frontier)
                    self._append_trace(
                        trace,
                        stage=f"AgentLoop[{step_index}].tool.adventure_clue",
                        summary="无进一步规则工具，执行一次线索语义工具并提交通过的线索事件。",
                        data={"event_types": [event.event_type for event in events]},
                    )
                stop_reason = "no_more_tools"
                break

            tool_key = self._tool_key(intent)
            if tool_key in executed_tool_keys:
                self._append_trace(
                    trace,
                    stage=f"AgentLoop[{step_index}].blocked",
                    summary="阻止重复工具调用，避免 ReAct 循环在同一 procedure/input 上打转。",
                    data={"procedure_id": intent.procedure_id, "inputs": intent.inputs},
                )
                stop_reason = "duplicate_tool_call_blocked"
                break
            executed_tool_keys.add(tool_key)
            procedure_result = self._run_native_procedure(
                session_id=request.session_id,
                state=state,
                intent=intent,
                actor_id=request.actor_id,
                trace_id=request.trace_id,
            )
            if procedure_result is None:
                stop_reason = "procedure_missing"
                break
            self._append_trace(
                trace,
                stage=f"AgentLoop[{step_index}].tool.procedure",
                summary="Runtime 执行规则工具；骰子、资源和状态变化以事件为准。",
                data={
                    "procedure_id": procedure_result.procedure_id,
                    "status": procedure_result.status,
                    "event_types": [event.event_type for event in procedure_result.events],
                    "message": procedure_result.message,
                },
            )
            history.append(
                {
                    "step_index": step_index,
                    "procedure_id": procedure_result.procedure_id,
                    "status": procedure_result.status,
                    "event_types": [event.event_type for event in procedure_result.events],
                    "passed": procedure_passed(procedure_result.events),
                }
            )
            if procedure_result.events:
                committed_events.extend(procedure_result.events)
                state = self._reducer.replay(state, procedure_result.events)
                post_events = self._post_process_procedure_events(
                    session_id=request.session_id,
                    state=state,
                    procedure_result=procedure_result,
                    trace_id=request.trace_id,
                )
                if post_events:
                    committed_events.extend(post_events)
                    state = self._reducer.replay(state, post_events)
            if request.adventure is not None and procedure_result.status == "completed":
                pending_clue_events = self._pending_clue_events_after_successful_procedure(
                    session_id=request.session_id,
                    adventure=request.adventure,
                    state=state,
                    procedure_result=procedure_result,
                    trace_id=request.trace_id,
                )
                if pending_clue_events:
                    committed_events.extend(pending_clue_events)
                    state = self._reducer.replay(state, pending_clue_events)
                    frontier = self._refresh_frontier(request.adventure, state, frontier)
            clue_decision, events, frontier = await self._resolve_clue_tool(
                request=request,
                state=state,
                frontier=frontier,
                procedure_result=procedure_result,
            )
            if events:
                committed_events.extend(events)
                state = self._reducer.replay(state, events)
                frontier = self._refresh_frontier(request.adventure, state, frontier)
            if procedure_result.status != "completed":
                stop_reason = procedure_result.status
                break
            if self._requires_player_choice(procedure_result.events, state):
                stop_reason = "awaiting_player_decision"
                break
            if not self._should_continue_after_procedure(procedure_result):
                stop_reason = "procedure_completed"
                break
            frontier = self._refresh_frontier(request.adventure, state, frontier)
        else:
            self._append_trace(
                trace,
                stage="AgentLoop.max_steps",
                summary="达到最大工具循环步数，停止继续调用工具。",
                data={"max_steps": request.max_steps},
            )
        return AgentLoopRunResult(
            intent=intent,
            state=state,
            frontier=frontier,
            committed_events=committed_events,
            clue_decision=clue_decision,
            procedure_result=procedure_result,
            agent_trace=trace,
            stop_reason=stop_reason,
        )

    def _run_mechanic_steps(
        self,
        *,
        request: AgentLoopRunRequest,
        state: SessionState,
        steps: list[Any],
        trace: list[AgentTraceStep],
        step_index: int,
    ) -> ProcedureExecutionResult | None:
        last_result: ProcedureExecutionResult | None = None
        for mechanic_step in steps:
            step_intent = IntentFrame(
                intent=mechanic_step.reason or mechanic_step.procedure_id,
                procedure_id=mechanic_step.procedure_id,
                actor_id=mechanic_step.actor_id,
                inputs=mechanic_step.inputs,
                confidence=1.0,
            )
            last_result = self._run_native_procedure(
                session_id=request.session_id,
                state=state,
                intent=step_intent,
                actor_id=mechanic_step.actor_id or request.actor_id,
                trace_id=request.trace_id,
            )
            if last_result is None:
                continue
            self._append_trace(
                trace,
                stage=f"AgentLoop[{step_index}].tool.mechanic_procedure",
                summary="执行 MechanicPlan 中的 Runtime procedure。",
                data={
                    "procedure_id": last_result.procedure_id,
                    "status": last_result.status,
                    "event_types": [event.event_type for event in last_result.events],
                },
            )
            if last_result.status != "completed":
                break
            if last_result.events:
                state = self._reducer.replay(state, last_result.events)
        return last_result

    def _post_process_procedure_events(
        self,
        *,
        session_id: str,
        state: SessionState,
        procedure_result: ProcedureExecutionResult,
        trace_id: str,
    ) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for event in procedure_result.events:
            if event.event_type == "AttackResolved":
                events.extend(
                    self._combat_scenes.start_after_attack(
                        session_id=session_id,
                        state=state,
                        attack_event=event,
                        trace_id=trace_id,
                    )
                )
        return events

    async def _resolve_clue_tool(
        self,
        *,
        request: AgentLoopRunRequest,
        state: SessionState,
        frontier: AdventureFrontier | None,
        procedure_result: ProcedureExecutionResult | None,
    ) -> tuple[ClueAcquisitionDecision | None, list[DomainEvent], AdventureFrontier | None]:
        if request.adventure is None or frontier is None or not request.can_advance_adventure:
            return None, [], frontier
        traced = TracedSemanticMatcher(matcher=self._semantic_matcher, trace_store=self._semantic_trace_store)
        clue_decision = await ClueAcquisitionEngine(traced).select_clue(
            player_action=request.player_message,
            available_clues=list(frontier.clues),
            trace_id=request.trace_id,
        )
        if clue_decision.clue is None:
            return clue_decision, [], frontier
        if self._can_commit_clue(clue=clue_decision.clue, procedure_result=procedure_result):
            events = self._adventures.clue_found_events(
                session_id=request.session_id,
                clue=clue_decision.clue,
                adventure=request.adventure,
                trace_id=request.trace_id,
            )
            events.extend(
                self._reveal_linked_handouts(
                    session_id=request.session_id,
                    adventure=request.adventure,
                    reveal_targets=[clue_decision.clue.id, clue_decision.clue.revelation_id],
                    trace_id=request.trace_id,
                )
            )
            return clue_decision, events, frontier
        pending = self._pending_clue_event(
            session_id=request.session_id,
            clue=clue_decision.clue,
            procedure_result=procedure_result,
            trace_id=request.trace_id,
        )
        return clue_decision, ([] if pending is None else [pending]), frontier

    def _refresh_frontier(
        self,
        adventure: AdventureIR | None,
        state: SessionState,
        fallback: AdventureFrontier | None,
    ) -> AdventureFrontier | None:
        if adventure is None:
            return fallback
        return self._adventures.frontier(adventure=adventure, state=state)

    def _reveal_linked_handouts(
        self,
        *,
        session_id: str,
        adventure: AdventureIR,
        reveal_targets: list[str],
        trace_id: str,
    ) -> list[DomainEvent]:
        target_set = set(reveal_targets)
        return [
            self._handouts.reveal_event(session_id=session_id, handout=handout, trace_id=trace_id)
            for handout in adventure.handouts
            if self._handout_reveals_any(handout, target_set)
        ]

    @staticmethod
    def _handout_reveals_any(handout: HandoutAsset, reveal_targets: set[str]) -> bool:
        return bool(set(handout.reveals).intersection(reveal_targets))

    @staticmethod
    def _run_native_procedure(
        *,
        session_id: str,
        state: SessionState,
        intent: IntentFrame,
        actor_id: str | None,
        trace_id: str,
    ) -> ProcedureExecutionResult | None:
        if intent.procedure_id is None:
            return None
        resolved_actor_id = actor_id or intent.actor_id or (state.party[0].id if state.party else None)
        if state.system_id == "coc7e":
            return Coc7eProcedureRunner().run(
                procedure_id=intent.procedure_id,
                session_id=session_id,
                state=state,
                actor_id=resolved_actor_id,
                inputs=intent.inputs,
                trace_id=trace_id,
            )
        return ProcedureExecutionResult(
            procedure_id=intent.procedure_id,
            status="unsupported",
            message="No native procedure runner is registered for this system.",
        )

    @staticmethod
    def _intent_with_bound_skill_call(intent: IntentFrame) -> IntentFrame:
        if intent.procedure_id is not None or not intent.skill_calls:
            return intent
        best_call = max(intent.skill_calls, key=lambda item: item.confidence)
        if best_call.tool_kind != "procedure" or best_call.procedure_id is None:
            return intent
        return intent.model_copy(
            update={
                "procedure_id": best_call.procedure_id,
                "inputs": best_call.inputs,
                "confidence": min(intent.confidence, best_call.confidence),
            }
        )

    @staticmethod
    def _can_commit_clue(*, clue: ClueCarrier, procedure_result: ProcedureExecutionResult | None) -> bool:
        if not clue.suggested_skills:
            return True
        if procedure_result is None or procedure_result.status != "completed":
            return False
        return procedure_passed(procedure_result.events) is True

    @staticmethod
    def _source_roll_event_id(procedure_result: ProcedureExecutionResult | None) -> str | None:
        if procedure_result is None:
            return None
        for event in procedure_result.events:
            if event.event_type in {"SkillRollResolved", "PushedRollResolved"}:
                return event.id
            if event.event_type == "LuckSpent":
                value = event.payload.get("source_event_id")
                return value if isinstance(value, str) else event.id
        return None

    @staticmethod
    def _procedure_passed(procedure_result: ProcedureExecutionResult | None) -> bool:
        if procedure_result is None or procedure_result.status != "completed":
            return False
        return procedure_passed(procedure_result.events) is True

    def _pending_clue_event(
        self,
        *,
        session_id: str,
        clue: ClueCarrier,
        procedure_result: ProcedureExecutionResult | None,
        trace_id: str,
    ) -> DomainEvent | None:
        if procedure_result is None or procedure_result.status != "completed" or self._procedure_passed(procedure_result):
            return None
        source_event_id = self._source_roll_event_id(procedure_result)
        if source_event_id is None:
            return None
        return DomainEvent(
            session_id=session_id,
            event_type="CluePending",
            payload={
                "clue_id": clue.id,
                "revelation_id": clue.revelation_id,
                "source_event_id": source_event_id,
                "reason": "matched clue gated by failed roll",
            },
            source_refs=clue.source_refs,
            trace_id=trace_id,
        )

    def _pending_clue_events_after_successful_procedure(
        self,
        *,
        session_id: str,
        adventure: AdventureIR,
        state: SessionState,
        procedure_result: ProcedureExecutionResult,
        trace_id: str,
    ) -> list[DomainEvent]:
        if not self._procedure_passed(procedure_result):
            return []
        roll_event_id = self._source_roll_event_id(procedure_result)
        events: list[DomainEvent] = []
        pending_items = [item for item in state.pending_clues if roll_event_id is None or item.get("source_event_id") == roll_event_id]
        for pending in pending_items:
            clue_id = pending.get("clue_id")
            clue = next((item for item in adventure.clues if item.id == clue_id), None)
            if clue is None or clue.id in state.discovered_clues:
                continue
            events.extend(
                self._adventures.clue_found_events(
                    session_id=session_id,
                    clue=clue,
                    adventure=adventure,
                    trace_id=trace_id,
                )
            )
            events.append(
                DomainEvent(
                    session_id=session_id,
                    event_type="PendingClueResolved",
                    payload={"clue_id": clue.id, "source_event_id": pending.get("source_event_id")},
                    trace_id=trace_id,
                )
            )
        return events

    @staticmethod
    def _requires_player_choice(events: list[DomainEvent], state: SessionState) -> bool:
        has_new_luck_decision = any(
            event.event_type in {"SkillRollResolved", "PushedRollResolved"}
            and event.payload.get("can_spend_luck") is True
            for event in events
        )
        return has_new_luck_decision or bool(state.pending_decisions)

    @staticmethod
    def _should_continue_after_procedure(procedure_result: ProcedureExecutionResult) -> bool:
        for event in procedure_result.events:
            if event.event_type == "SanityRollResolved":
                return bool(
                    event.payload.get("temporary_insanity")
                    or event.payload.get("indefinite_insanity")
                    or event.payload.get("involuntary_action")
                )
        return False

    @staticmethod
    def _tool_key(intent: IntentFrame) -> str:
        return f"{intent.procedure_id}|{sorted(intent.inputs.items(), key=lambda item: item[0])}"

    @staticmethod
    def _append_trace(
        steps: list[AgentTraceStep],
        *,
        stage: str,
        summary: str,
        data: dict[str, object] | None = None,
    ) -> None:
        steps.append(
            AgentTraceStep(
                step=len(steps) + 1,
                stage=stage,
                summary=summary,
                data={} if data is None else data,
            )
        )
