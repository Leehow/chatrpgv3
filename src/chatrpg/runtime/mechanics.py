from __future__ import annotations

import orjson
from typing import Any

from chatrpg.core.ids import new_id
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.mechanics import (
    ActionFrame,
    AssetRequirement,
    EntityMention,
    MechanicPlan,
    MechanicStep,
    ResolvedMechanicPlan,
    SceneFrame,
    TriggeredAffordance,
)
from chatrpg.ir.state import CharacterState, SessionState
from chatrpg.retrieval.semantic import SemanticCandidate, SemanticMatchRequest, SemanticMatchResult


class MechanicTriggerJudge:
    def __init__(self, semantic_matcher: Any) -> None:
        self._semantic_matcher = semantic_matcher

    async def judge(
        self,
        *,
        action: ActionFrame,
        scene: SceneFrame,
        trace_id: str,
    ) -> MechanicPlan:
        candidates = [
            SemanticCandidate(
                id=affordance.id,
                label=f"{affordance.trigger_kind}: {affordance.trigger_description}",
                description=affordance.trigger_description,
                metadata={
                    "trigger_kind": affordance.trigger_kind,
                    "subject_ref": None if affordance.subject_ref is None else affordance.subject_ref.model_dump(mode="json"),
                    "procedure_candidates": affordance.procedure_candidates,
                    "priority": affordance.priority,
                },
            )
            for affordance in scene.active_affordances
        ]
        if not candidates:
            return MechanicPlan(status="no_trigger", reason="No mechanic affordances are active in the current scene.")
        query = orjson.dumps(
            {
                "action": action.model_dump(mode="json"),
                "scene": {
                    "actors": [actor.model_dump(mode="json") for actor in scene.present_actors],
                    "active_unit_ids": scene.active_unit_ids,
                    "recent_event_types": scene.recent_event_types,
                },
            }
        ).decode("utf-8")
        result = await self._semantic_matcher.match(
            SemanticMatchRequest(
                task="mechanic.trigger",
                query=query,
                candidates=candidates,
                instructions=(
                    "Choose the active mechanic affordance that should trigger from the player's current action and scene. "
                    "Use semantic meaning and fictional positioning only. Do not use keyword or substring matching. "
                    "Return no_match if the action is ordinary narration and no rule mechanism should fire."
                ),
                confidence_floor=0.72,
            ),
            trace_id=trace_id,
        )
        return self._plan_from_match(result=result, scene=scene)

    @staticmethod
    def _plan_from_match(*, result: SemanticMatchResult, scene: SceneFrame) -> MechanicPlan:
        if result.status != "matched" or not result.choices:
            return MechanicPlan(status=result.status if result.status in {"ambiguous", "no_match"} else "no_trigger", reason="No mechanic trigger matched with sufficient semantic confidence.")
        choice = max(result.choices, key=lambda item: item.confidence)
        affordance = next((item for item in scene.active_affordances if item.id == choice.candidate_id), None)
        if affordance is None:
            return MechanicPlan(status="invalid", reason="Semantic match referred to an unavailable affordance.")
        return MechanicPlan(
            status="planned",
            reason=choice.rationale,
            triggers=[
                TriggeredAffordance(
                    affordance_id=affordance.id,
                    trigger_kind=affordance.trigger_kind,
                    confidence=choice.confidence,
                    rationale=choice.rationale,
                    source_refs=affordance.source_refs,
                )
            ],
            ordered_steps=[
                MechanicStep(
                    procedure_id=procedure_id,
                    inputs=dict(affordance.default_inputs),
                    reason=affordance.trigger_description,
                )
                for procedure_id in affordance.procedure_candidates
            ],
            required_assets=[
                AssetRequirement(
                    kind=requirement,
                    entity_ref=affordance.subject_ref,
                    resolution_policy="synthesize" if requirement in {"target_actor_id", "target_hp"} else "explicit",
                    reason=affordance.trigger_description,
                )
                for requirement in affordance.parameter_requirements
            ],
            source_refs=affordance.source_refs,
            confidence=choice.confidence,
        )


class ParameterResolver:
    def resolve(
        self,
        *,
        session_id: str,
        state: SessionState,
        plan: MechanicPlan,
        scene: SceneFrame,
        actor_id: str | None,
        trace_id: str,
    ) -> ResolvedMechanicPlan:
        pre_events: list[DomainEvent] = []
        steps: list[MechanicStep] = []
        for step in plan.ordered_steps:
            inputs = dict(step.inputs)
            subject_id = self._subject_id(plan)
            if subject_id is not None:
                runtime_actor_id, created_event = self._resolve_runtime_actor(
                    session_id=session_id,
                    state=state,
                    scene=scene,
                    source_entity_id=subject_id,
                    trace_id=trace_id,
                )
                if created_event is not None:
                    pre_events.append(created_event)
                    actor_payload = created_event.payload.get("actor")
                    if isinstance(actor_payload, dict):
                        state.runtime_actors.append(CharacterState.model_validate(actor_payload))
                inputs = self._replace_subject_placeholders(inputs=inputs, runtime_actor_id=runtime_actor_id)
            if step.procedure_id == "coc7e.sanity_roll":
                inputs.setdefault("success_loss", 0)
                inputs.setdefault("failure_loss", {"count": 1, "sides": 4, "modifier": 0})
            steps.append(step.model_copy(update={"actor_id": actor_id or step.actor_id, "inputs": inputs}))
        return ResolvedMechanicPlan(plan=plan, pre_events=pre_events, steps=steps)

    @staticmethod
    def _subject_id(plan: MechanicPlan) -> str | None:
        for requirement in plan.required_assets:
            if requirement.entity_ref is not None:
                return requirement.entity_ref.id
        return None

    def _resolve_runtime_actor(
        self,
        *,
        session_id: str,
        state: SessionState,
        scene: SceneFrame,
        source_entity_id: str,
        trace_id: str,
    ) -> tuple[str, DomainEvent | None]:
        for actor in state.runtime_actors:
            if actor.traits.get("source_entity_id") == source_entity_id:
                return actor.id, None
        presence = next((actor for actor in scene.present_actors if actor.ref.id == source_entity_id), None)
        if presence is not None and presence.runtime_actor_id is not None:
            return presence.runtime_actor_id, None
        name = source_entity_id if presence is None else presence.name
        runtime_actor = _civilian_actor(source_entity_id=source_entity_id, name=name)
        event = DomainEvent(
            session_id=session_id,
            event_type="RuntimeActorCreated",
            actor_id=runtime_actor.id,
            payload={
                "actor": runtime_actor.model_dump(mode="json"),
                "provenance": {
                    "kind": "synthesized",
                    "basis": ["scene actor presence", "system civilian baseline"],
                    "confidence": 0.70,
                    "reviewer_required": False,
                },
            },
            trace_id=trace_id,
        )
        return runtime_actor.id, event

    @staticmethod
    def _replace_subject_placeholders(*, inputs: dict[str, object], runtime_actor_id: str) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in inputs.items():
            if value == "__subject__":
                result[key] = runtime_actor_id
            else:
                result[key] = value
        return result


def action_frame_from_intent(*, message: str, actor_id: str | None, intent: object) -> ActionFrame:
    targets: list[EntityMention] = []
    target_values = getattr(intent, "targets", [])
    if isinstance(target_values, list):
        targets = [EntityMention(text=value, confidence=0.5) for value in target_values if isinstance(value, str)]
    return ActionFrame(
        actor_id=actor_id or getattr(intent, "actor_id", None),
        raw_text=message,
        intent=getattr(intent, "intent", ""),
        targets=targets,
    )


def _civilian_actor(*, source_entity_id: str, name: str) -> CharacterState:
    return CharacterState(
        id=new_id("npc"),
        name=name,
        owner="runtime_npc",
        resources={"hp": 10, "hp_max": 10, "sanity": 50},
        traits={
            "source_entity_id": source_entity_id,
            "archetype": "civilian_npc",
            "str": 40,
            "con": 50,
            "siz": 50,
            "dex": 45,
            "int": 60,
            "pow": 50,
            "move": 7,
            "build": 0,
            "damage_bonus": "0",
        },
        skills={
            "dodge": 22,
            "fighting_brawl": 25,
            "listen": 25,
            "spot_hidden": 25,
            "psychology": 30,
            "persuade": 40,
        },
        conditions=[],
    )
