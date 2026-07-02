from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState, SessionState
from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.systems.coc7e.advanced import (
    ChaseParticipant,
    CocChaseEngine,
    CocCombatEngine,
    CocDevelopmentEngine,
    CocMythosEngine,
)
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
        if procedure_id == "coc7e.opposed_roll":
            return self._opposed_roll(
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
        if procedure_id == "coc7e.chase_round":
            return self._chase_round(
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
        if procedure_id == "coc7e.first_aid":
            return self._recovery_roll(
                procedure_id=procedure_id,
                event_type="FirstAidResolved",
                default_skill_id="first_aid",
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
            )
        if procedure_id == "coc7e.medicine":
            return self._recovery_roll(
                procedure_id=procedure_id,
                event_type="MedicineResolved",
                default_skill_id="medicine",
                session_id=session_id,
                state=state,
                actor_id=actor_id,
                inputs=inputs,
                trace_id=trace_id,
            )
        if procedure_id == "coc7e.bout_of_madness":
            return self._bout_of_madness(
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
                self._resource_event(
                    session_id=session_id,
                    actor_id=actor.id,
                    resource_id="luck",
                    delta=-luck_spent,
                    trace_id=trace_id,
                )
            )
        return self._completed(procedure_id, events)

    def _opposed_roll(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        attacker = self._character(state, actor_id or self._string(inputs.get("attacker_id")))
        defender = self._character(state, self._string(inputs.get("defender_id")))
        attacker_target = self._optional_int(inputs.get("attacker_target"))
        defender_target = self._optional_int(inputs.get("defender_target"))
        if attacker is not None and attacker_target is None:
            attacker_target = self._target_from_character(actor=attacker, skill_id=self._string(inputs.get("attacker_skill_id")), trait_id=self._string(inputs.get("attacker_trait_id")))
        if defender is not None and defender_target is None:
            defender_target = self._target_from_character(actor=defender, skill_id=self._string(inputs.get("defender_skill_id")), trait_id=self._string(inputs.get("defender_trait_id")))
        if attacker_target is None or defender_target is None:
            return self._invalid(procedure_id, "Opposed rolls require attacker and defender targets.")
        result = self._coc.opposed_roll(
            attacker_target=attacker_target,
            defender_target=defender_target,
            reason=self._reason(inputs=inputs, fallback="opposed roll"),
        )
        return self._completed(
            procedure_id,
            [
                DomainEvent(
                    session_id=session_id,
                    event_type="OpposedRollResolved",
                    actor_id=None if attacker is None else attacker.id,
                    payload=result.model_dump(mode="json"),
                    trace_id=trace_id,
                )
            ],
        )

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
                self._condition_event(
                    session_id=session_id,
                    actor_id=actor.id,
                    condition=condition,
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

    def _chase_round(
        self,
        *,
        procedure_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        participants_payload = inputs.get("participants")
        if not isinstance(participants_payload, list) or not participants_payload:
            return self._invalid(procedure_id, "Chase rounds require participants.")
        participants = []
        for item in participants_payload:
            if isinstance(item, dict):
                participant_id = self._string(item.get("id"))
                role = self._string(item.get("role"))
                move = self._optional_int(item.get("move"))
                dex = self._int(item.get("dex"), 0)
                if participant_id and role in {"pursuer", "quarry"} and move is not None:
                    participants.append(ChaseParticipant(id=participant_id, role=role, move=move, dex=dex))
        if not participants:
            return self._invalid(procedure_id, "Chase participants are malformed.")
        chase = CocChaseEngine()
        round_result = chase.order_participants(participants)
        movement_actor = self._character(state, self._string(inputs.get("movement_actor_id")) or actor_id)
        movement_target = self._optional_int(inputs.get("target"))
        if movement_actor is not None and movement_target is None:
            movement_target = self._target_from_character(
                actor=movement_actor,
                skill_id=self._string(inputs.get("skill_id")),
                trait_id=self._string(inputs.get("trait_id")),
            )
        if movement_actor is not None and movement_target is not None:
            movement_round = chase.movement_check(
                coc=self._coc,
                participant_id=movement_actor.id,
                target=movement_target,
                reason=self._reason(inputs=inputs, fallback="chase movement"),
            )
            round_result.checks.extend(movement_round.checks)
            round_result.gap_changes.update(movement_round.gap_changes)
        return self._completed(
            procedure_id,
            [
                DomainEvent(
                    session_id=session_id,
                    event_type="ChaseRoundResolved",
                    actor_id=None if movement_actor is None else movement_actor.id,
                    payload=round_result.model_dump(mode="json"),
                    trace_id=trace_id,
                )
            ],
        )

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

    def _recovery_roll(
        self,
        *,
        procedure_id: str,
        event_type: str,
        default_skill_id: str,
        session_id: str,
        state: SessionState,
        actor_id: str | None,
        inputs: dict[str, Any],
        trace_id: str,
    ) -> ProcedureExecutionResult:
        actor = self._character(state, actor_id)
        target_actor = self._character(state, self._string(inputs.get("target_actor_id"))) or actor
        if actor is None or target_actor is None:
            return self._invalid(procedure_id, "Recovery procedures require an actor and target.")
        skill_id = self._string(inputs.get("skill_id")) or default_skill_id
        roll = self._coc.skill_roll(
            target=actor.skills.get(skill_id, 0),
            reason=self._reason(inputs=inputs, fallback=procedure_id),
            allow_luck=False,
        )
        heal_amount = self._healing_amount(inputs=inputs) if roll.passed else 0
        hp_before = target_actor.resources.get("hp", 0)
        hp_after = hp_before + heal_amount
        events = [
            DomainEvent(
                session_id=session_id,
                event_type=event_type,
                actor_id=actor.id,
                payload={
                    "target_actor_id": target_actor.id,
                    "skill_id": skill_id,
                    "roll": roll.model_dump(mode="json"),
                    "healing": heal_amount,
                    "hp_before": hp_before,
                    "hp_after": hp_after,
                },
                trace_id=trace_id,
            )
        ]
        if heal_amount:
            events.append(self._resource_event(session_id=session_id, actor_id=target_actor.id, resource_id="hp", delta=heal_amount, trace_id=trace_id))
        if roll.passed and "dying" in target_actor.conditions:
            events.append(self._condition_removed_event(session_id=session_id, actor_id=target_actor.id, condition="dying", trace_id=trace_id))
        return self._completed(procedure_id, events)

    def _bout_of_madness(
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
            return self._invalid(procedure_id, "Bout of madness requires an actor.")
        table_roll = self._dice.integer(low=1, high=10, reason=self._reason(inputs=inputs, fallback="bout of madness"))
        mode = self._string(inputs.get("mode")) or "real_time"
        condition = f"bout_of_madness_{table_roll}"
        return self._completed(
            procedure_id,
            [
                DomainEvent(
                    session_id=session_id,
                    event_type="BoutOfMadnessResolved",
                    actor_id=actor.id,
                    payload={"table_roll": table_roll, "mode": mode, "condition": condition},
                    trace_id=trace_id,
                ),
                self._condition_event(session_id=session_id, actor_id=actor.id, condition=condition, trace_id=trace_id),
            ],
        )

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

    @classmethod
    def _target_from_character(cls, *, actor: CharacterState, skill_id: str | None, trait_id: str | None) -> int | None:
        if skill_id:
            return actor.skills.get(skill_id, 0)
        if trait_id:
            return cls._optional_int(actor.traits.get(trait_id))
        return None

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

    @classmethod
    def _healing_amount(cls, *, inputs: dict[str, Any]) -> int:
        constant = cls._optional_int(inputs.get("healing"))
        if constant is not None:
            return max(0, constant)
        request = cls._dice_request(inputs.get("healing_roll"))
        if request is None:
            return 1
        return max(0, sum(request.modifier + roll for roll in ()))

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
    def _condition_removed_event(*, session_id: str, actor_id: str, condition: str, trace_id: str) -> DomainEvent:
        return DomainEvent(
            session_id=session_id,
            event_type="CharacterConditionRemoved",
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
