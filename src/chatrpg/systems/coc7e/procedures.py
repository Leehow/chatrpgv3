from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState, SessionState
from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.systems.coc7e.advanced import CocCombatEngine, CocDevelopmentEngine, CocMythosEngine
from chatrpg.systems.coc7e.runtime import Coc7eEngine, CocDifficulty, SanityLossSpec

ExecutionStatus = Literal["completed", "unsupported", "invalid"]


class ProcedureExecutionResult(BaseModel):
    procedure_id: str
    status: ExecutionStatus
    events: list[DomainEvent] = Field(default_factory=list)
    message: str | None = None


class Coc7eProcedureRunner:
    def __init__(self, dice: DiceEngine | None = None) -> None:
        self._dice = dice or DiceEngine()
        self._coc = Coc7eEngine(self._dice)

    def run(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        if procedure_id == "coc7e.skill_roll":
            return self._skill_roll(
                procedure_id=procedure_id,
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
                pushed=False,
            )
        if procedure_id == "coc7e.pushed_roll":
            return self._skill_roll(
                procedure_id=procedure_id,
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
                pushed=True,
            )
        if procedure_id == "coc7e.luck_spend":
            return self._luck_spend(
                procedure_id=procedure_id,
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
            )
        if procedure_id == "coc7e.sanity_roll":
            return self._sanity_roll(
                procedure_id=procedure_id,
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
            )
        if procedure_id == "coc7e.combat_attack":
            return self._combat_attack(
                procedure_id=procedure_id,
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
            )
        if procedure_id == "coc7e.cast_spell":
            return self._cast_spell(
                procedure_id=procedure_id,
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
            )
        if procedure_id == "coc7e.study_tome":
            return self._study_tome(
                procedure_id=procedure_id,
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
            )
        if procedure_id == "coc7e.investigator_development":
            return self._development(
                procedure_id=procedure_id,
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
            )
        return ProcedureExecutionResult(
            procedure_id=procedure_id,
            status="unsupported",
            message="No native CoC 7e runner is registered for this procedure.",
        )

    def _skill_roll(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
        pushed: bool,
    ) -> ProcedureExecutionResult:
        actor = self._character(state, actor_id)
        if actor is None:
            return self._invalid(procedure_id, "No actor character is available for the skill roll.")
        target, target_ref = self._roll_target(actor=actor, inputs=inputs)
        if target is None:
            return self._invalid(procedure_id, "No skill, trait, or numeric target was supplied for the skill roll.")
        difficulty = self._difficulty(inputs.get("difficulty"))
        reason = self._reason(inputs=inputs, fallback=procedure_id)
        if pushed:
            result = self._coc.pushed_roll(target=target, reason=reason, difficulty=difficulty)
            event_type = "PushedRollResolved"
        else:
            result = self._coc.skill_roll(
                target=target,
                reason=reason,
                bonus_dice=self._int(inputs.get("bonus_dice"), 0),
                penalty_dice=self._int(inputs.get("penalty_dice"), 0),
                difficulty=difficulty,
            )
            event_type = "SkillRollResolved"
        payload = result.model_dump(mode="json")
        payload["target_ref"] = target_ref
        payload["ignored_player_claims"] = self._ignored_player_claims(inputs)
        return self._completed(
            procedure_id,
            [
                DomainEvent(
                    session_id=session_id,
                    event_type=event_type,
                    actor_id=actor.id,
                    payload=payload,
                    trace_id=trace_id,
                )
            ],
        )

    def _luck_spend(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        actor = self._character(state, actor_id)
        if actor is None:
            return self._invalid(procedure_id, "No actor character is available for Luck spending.")
        original_roll = self._optional_int(inputs.get("roll")) or self._optional_int(inputs.get("original_roll"))
        target, target_ref = self._roll_target(actor=actor, inputs=inputs)
        if original_roll is None or target is None:
            return self._invalid(procedure_id, "Luck spending requires an original roll and a target.")
        difficulty = self._difficulty(inputs.get("difficulty"))
        threshold = {"regular": target, "hard": target // 2, "extreme": target // 5}[difficulty]
        luck_needed = max(0, original_roll - threshold)
        current_luck = actor.resources.get("luck", 0)
        luck_spent = min(current_luck, luck_needed)
        adjusted_roll = original_roll - luck_spent
        events = [
            DomainEvent(
                session_id=session_id,
                event_type="LuckSpent",
                actor_id=actor.id,
                payload={
                    "original_roll": original_roll,
                    "adjusted_roll": adjusted_roll,
                    "target": target,
                    "target_ref": target_ref,
                    "difficulty": difficulty,
                    "luck_spent": luck_spent,
                    "new_luck": current_luck - luck_spent,
                },
                trace_id=trace_id,
            )
        ]
        if luck_spent:
            events.append(
                DomainEvent(
                    session_id=session_id,
                    event_type="CharacterResourceChanged",
                    actor_id=actor.id,
                    payload={"resource_id": "luck", "delta": -luck_spent},
                    trace_id=trace_id,
                )
            )
        return self._completed(procedure_id, events)

    def _sanity_roll(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        actor = self._character(state, actor_id)
        if actor is None:
            return self._invalid(procedure_id, "No actor character is available for the SAN roll.")
        current_sanity = actor.resources.get("sanity", 0)
        result = self._coc.sanity_roll(
            current_sanity=current_sanity,
            success_loss=self._loss_spec(inputs.get("success_loss"), 0),
            failure_loss=self._loss_spec(inputs.get("failure_loss"), 1),
            reason=self._reason(inputs=inputs, fallback="SAN roll"),
            starting_sanity_for_day=self._optional_int(inputs.get("starting_sanity_for_day")),
            int_target=self._optional_int(actor.traits.get("int")),
        )
        events = [
            DomainEvent(
                session_id=session_id,
                event_type="SanityRollResolved",
                actor_id=actor.id,
                payload=result.model_dump(mode="json"),
                trace_id=trace_id,
            )
        ]
        if result.sanity_lost:
            events.append(
                DomainEvent(
                    session_id=session_id,
                    event_type="CharacterResourceChanged",
                    actor_id=actor.id,
                    payload={"resource_id": "sanity", "delta": -result.sanity_lost, "after": result.sanity_after},
                    trace_id=trace_id,
                )
            )
        for condition in self._sanity_conditions(result):
            events.append(
                DomainEvent(
                    session_id=session_id,
                    event_type="CharacterConditionAdded",
                    actor_id=actor.id,
                    payload={"condition": condition},
                    trace_id=trace_id,
                )
            )
        return self._completed(procedure_id, events)

    def _combat_attack(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        actor = self._character(state, actor_id)
        if actor is None:
            return self._invalid(procedure_id, "No actor character is available for the attack.")
        attack_target, target_ref = self._roll_target(actor=actor, inputs=inputs)
        damage = self._dice_request(inputs.get("damage"))
        if attack_target is None or damage is None:
            return self._invalid(procedure_id, "Combat attacks require an attack target and a damage dice request.")
        defender = self._character(state, self._string(inputs.get("target_actor_id")))
        defender_hp = self._optional_int(inputs.get("target_hp"))
        if defender is not None:
            defender_hp = defender.resources.get("hp", 0)
        if defender_hp is None:
            return self._invalid(procedure_id, "Combat attacks require target_hp or a target_actor_id.")
        settlement = CocCombatEngine(self._coc, self._dice).settle_attack(
            target=attack_target,
            damage=damage,
            target_hp=defender_hp,
            reason=self._reason(inputs=inputs, fallback="combat attack"),
            armor=self._int(inputs.get("armor"), 0),
            bonus_dice=self._int(inputs.get("bonus_dice"), 0),
            penalty_dice=self._int(inputs.get("penalty_dice"), 0),
        )
        payload = settlement.model_dump(mode="json")
        payload["target_ref"] = target_ref
        if defender is not None:
            payload["target_actor_id"] = defender.id
        events = [
            DomainEvent(
                session_id=session_id,
                event_type="AttackResolved",
                actor_id=actor.id,
                payload=payload,
                trace_id=trace_id,
            )
        ]
        if defender is not None and settlement.applied_damage:
            events.append(
                DomainEvent(
                    session_id=session_id,
                    event_type="CharacterResourceChanged",
                    actor_id=defender.id,
                    payload={"resource_id": "hp", "delta": -settlement.applied_damage, "after": settlement.target_hp_after},
                    trace_id=trace_id,
                )
            )
        if defender is not None and settlement.major_wound:
            events.append(self._condition_event(session_id=session_id, actor_id=defender.id, condition="major_wound", trace_id=trace_id))
        if defender is not None and settlement.dead:
            events.append(self._condition_event(session_id=session_id, actor_id=defender.id, condition="dead", trace_id=trace_id))
        return self._completed(procedure_id, events)

    def _cast_spell(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        actor = self._character(state, actor_id)
        if actor is None:
            return self._invalid(procedure_id, "No actor character is available for spell casting.")
        sanity_cost = self._dice_request(inputs.get("sanity_cost")) or DiceRequest(count=1, sides=2, modifier=-1)
        result = CocMythosEngine(self._coc, self._dice).cast_spell(
            current_mp=actor.resources.get("mp", 0),
            mp_cost=self._int(inputs.get("mp_cost"), 0),
            sanity_cost=sanity_cost,
            reason=self._reason(inputs=inputs, fallback="spell casting"),
            power_roll_target=self._optional_int(inputs.get("power_roll_target")),
        )
        events = [
            DomainEvent(
                session_id=session_id,
                event_type="SpellCastResolved",
                actor_id=actor.id,
                payload=result.model_dump(mode="json"),
                trace_id=trace_id,
            )
        ]
        if result.mp_spent:
            events.append(self._resource_event(session_id=session_id, actor_id=actor.id, resource_id="mp", delta=-result.mp_spent, trace_id=trace_id))
        if result.sanity_spent:
            events.append(self._resource_event(session_id=session_id, actor_id=actor.id, resource_id="sanity", delta=-result.sanity_spent, trace_id=trace_id))
        return self._completed(procedure_id, events)

    def _study_tome(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        actor = self._character(state, actor_id)
        if actor is None:
            return self._invalid(procedure_id, "No actor character is available for tome study.")
        sanity_loss = self._dice_request(inputs.get("sanity_loss")) or DiceRequest(count=1, sides=2, modifier=-1)
        result = CocMythosEngine(self._coc, self._dice).study_tome(
            title=self._string(inputs.get("title")) or "Unknown Tome",
            weeks_required=self._int(inputs.get("weeks_required"), 0),
            mythos_gain=self._int(inputs.get("mythos_gain"), 0),
            sanity_loss=sanity_loss,
            reason=self._reason(inputs=inputs, fallback="tome study"),
        )
        events = [
            DomainEvent(
                session_id=session_id,
                event_type="TomeStudyResolved",
                actor_id=actor.id,
                payload=result.model_dump(mode="json"),
                trace_id=trace_id,
            )
        ]
        if result.sanity_loss:
            events.append(self._resource_event(session_id=session_id, actor_id=actor.id, resource_id="sanity", delta=-result.sanity_loss, trace_id=trace_id))
        if result.mythos_gain:
            events.append(
                DomainEvent(
                    session_id=session_id,
                    event_type="CharacterSkillChanged",
                    actor_id=actor.id,
                    payload={"skill_id": "cthulhu_mythos", "delta": result.mythos_gain},
                    trace_id=trace_id,
                )
            )
        return self._completed(procedure_id, events)

    def _development(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        actor = self._character(state, actor_id)
        skill_id = self._string(inputs.get("skill_id"))
        if actor is None or not skill_id:
            return self._invalid(procedure_id, "Investigator development requires an actor and skill_id.")
        current_value = actor.skills.get(skill_id, self._int(inputs.get("current_value"), 0))
        result = CocDevelopmentEngine(self._coc, self._dice).improve_skill(
            skill_id=skill_id,
            current_value=current_value,
            reason=self._reason(inputs=inputs, fallback="investigator development"),
        )
        events = [
            DomainEvent(
                session_id=session_id,
                event_type="SkillImprovementResolved",
                actor_id=actor.id,
                payload=result.model_dump(mode="json"),
                trace_id=trace_id,
            )
        ]
        if result.improved:
            events.append(
                DomainEvent(
                    session_id=session_id,
                    event_type="CharacterSkillChanged",
                    actor_id=actor.id,
                    payload={"skill_id": skill_id, "value": result.new_value},
                    trace_id=trace_id,
                )
            )
        return self._completed(procedure_id, events)

    @staticmethod
    def _completed(procedure_id: str, events: list[DomainEvent]) -> ProcedureExecutionResult:
        return ProcedureExecutionResult(procedure_id=procedure_id, status="completed", events=events)

    @staticmethod
    def _invalid(procedure_id: str, message: str) -> ProcedureExecutionResult:
        return ProcedureExecutionResult(procedure_id=procedure_id, status="invalid", message=message)

    @staticmethod
    def _character(state: SessionState, actor_id: str | None) -> CharacterState | None:
        if actor_id is None:
            return state.party[0] if state.party else None
        return next((character for character in state.party if character.id == actor_id or character.owner == actor_id), None)

    @classmethod
    def _roll_target(cls, *, actor: CharacterState, inputs: dict[str, Any]) -> tuple[int | None, dict[str, object] | None]:
        skill_id = cls._string(inputs.get("skill_id"))
        if skill_id:
            return actor.skills.get(skill_id, 0), {"kind": "skill", "id": skill_id}
        trait_id = cls._string(inputs.get("trait_id"))
        if trait_id:
            value = cls._optional_int(actor.traits.get(trait_id))
            return value, {"kind": "trait", "id": trait_id}
        direct = cls._optional_int(inputs.get("target"))
        if direct is not None:
            return direct, {"kind": "direct", "id": "target"}
        return None, None

    @staticmethod
    def _difficulty(value: object) -> CocDifficulty:
        return value if value in {"regular", "hard", "extreme"} else "regular"

    @classmethod
    def _dice_request(cls, value: object) -> DiceRequest | None:
        if not isinstance(value, dict):
            return None
        count = cls._optional_int(value.get("count"))
        sides = cls._optional_int(value.get("sides"))
        modifier = cls._int(value.get("modifier"), 0)
        if count is None or sides is None:
            return None
        return DiceRequest(count=count, sides=sides, modifier=modifier)

    @classmethod
    def _loss_spec(cls, value: object, fallback: int) -> SanityLossSpec:
        if isinstance(value, int):
            return value
        if isinstance(value, dict):
            constant = cls._optional_int(value.get("constant"))
            if constant is not None:
                return constant
            request = cls._dice_request(value)
            if request is not None:
                return request
        return fallback

    @staticmethod
    def _sanity_conditions(result: object) -> list[str]:
        conditions: list[str] = []
        if getattr(result, "temporary_insanity", False):
            conditions.append("temporary_insanity")
        if getattr(result, "indefinite_insanity", False):
            conditions.append("indefinite_insanity")
        if getattr(result, "sanity_after", 1) == 0:
            conditions.append("permanent_insanity")
        return conditions

    @staticmethod
    def _resource_event(*, session_id: str, actor_id: str, resource_id: str, delta: int, trace_id: str) -> DomainEvent:
        return DomainEvent(
            session_id=session_id,
            event_type="CharacterResourceChanged",
            actor_id=actor_id,
            payload={"resource_id": resource_id, "delta": delta},
            trace_id=trace_id,
        )

    @staticmethod
    def _condition_event(*, session_id: str, actor_id: str, condition: str, trace_id: str) -> DomainEvent:
        return DomainEvent(
            session_id=session_id,
            event_type="CharacterConditionAdded",
            actor_id=actor_id,
            payload={"condition": condition},
            trace_id=trace_id,
        )

    @staticmethod
    def _reason(*, inputs: dict[str, Any], fallback: str) -> str:
        value = inputs.get("reason")
        return value if isinstance(value, str) and value else fallback

    @staticmethod
    def _string(value: object) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        return None

    @classmethod
    def _int(cls, value: object, fallback: int) -> int:
        resolved = cls._optional_int(value)
        return fallback if resolved is None else resolved

    @staticmethod
    def _ignored_player_claims(inputs: dict[str, Any]) -> dict[str, object]:
        ignored: dict[str, object] = {}
        for key in ("roll", "rolled", "dice_result", "success_level", "claimed_result"):
            value = inputs.get(key)
            if value is not None:
                ignored[key] = value
        return ignored
