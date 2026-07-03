from __future__ import annotations

from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.mechanics import ActorPresence, EntityRef, MechanicAffordance, SceneFrame
from chatrpg.ir.state import CharacterState, SessionState
from chatrpg.runtime.adventure import AdventureFrontier


class SceneFrameBuilder:
    def build(
        self,
        *,
        state: SessionState,
        adventure: AdventureIR | None,
        frontier: AdventureFrontier | None,
        recent_event_types: list[str] | None = None,
    ) -> SceneFrame:
        active_unit_ids = [] if frontier is None else [unit.id for unit in frontier.units]
        present_actors = [_player_presence(character) for character in state.party]
        present_actors.extend(_runtime_presence(character) for character in state.runtime_actors)
        if adventure is not None and frontier is not None:
            unit_ids = set(active_unit_ids)
            for npc in adventure.npcs:
                if unit_ids.intersection(npc.unit_ids):
                    runtime_actor = _runtime_actor_for_entity(state=state, entity_id=npc.id)
                    present_actors.append(
                        ActorPresence(
                            ref=EntityRef(kind="npc", id=npc.id, label=npc.name),
                            name=npc.name,
                            role="scenario_npc",
                            visibility="player_visible",
                            runtime_actor_id=None if runtime_actor is None else runtime_actor.id,
                            summary=npc.public_profile or npc.summary,
                        )
                    )
        affordances = [] if adventure is None else _active_adventure_affordances(adventure=adventure, active_unit_ids=active_unit_ids)
        affordances.extend(_system_affordances_for_present_actors(present_actors))
        return SceneFrame(
            scene_id="current_scene",
            active_unit_ids=active_unit_ids,
            present_actors=present_actors,
            active_affordances=affordances,
            recent_event_types=recent_event_types or [],
        )


def _player_presence(character: CharacterState) -> ActorPresence:
    return ActorPresence(
        ref=EntityRef(kind="player_character", id=character.id, label=character.name),
        name=character.name,
        role="player_character",
        visibility="player_visible",
        runtime_actor_id=character.id,
        summary=None,
    )


def _runtime_presence(character: CharacterState) -> ActorPresence:
    linked_entity_id = character.traits.get("source_entity_id")
    ref_id = linked_entity_id if isinstance(linked_entity_id, str) else character.id
    return ActorPresence(
        ref=EntityRef(kind="runtime_actor", id=ref_id, label=character.name),
        name=character.name,
        role="runtime_actor",
        visibility="keeper_only",
        runtime_actor_id=character.id,
        summary=None,
    )


def _runtime_actor_for_entity(*, state: SessionState, entity_id: str) -> CharacterState | None:
    for actor in state.runtime_actors:
        if actor.traits.get("source_entity_id") == entity_id:
            return actor
    return None


def _active_adventure_affordances(*, adventure: AdventureIR, active_unit_ids: list[str]) -> list[MechanicAffordance]:
    unit_ids = set(active_unit_ids)
    result: list[MechanicAffordance] = []
    for affordance in adventure.affordances:
        unit_id = affordance.default_inputs.get("unit_id")
        if not isinstance(unit_id, str) or unit_id in unit_ids:
            result.append(affordance)
    return result


def _system_affordances_for_present_actors(present_actors: list[ActorPresence]) -> list[MechanicAffordance]:
    result: list[MechanicAffordance] = []
    for actor in present_actors:
        if actor.ref.kind == "player_character":
            continue
        subject = actor.ref
        result.append(
            MechanicAffordance(
                id=f"system.coc7e.aggression.{subject.id}",
                trigger_kind="aggression",
                subject_ref=subject,
                trigger_description=(
                    f"A player character uses physical violence, a weapon, a surprise blow, a forceful restraint, "
                    f"or another hostile action against {actor.name}."
                ),
                procedure_candidates=["coc7e.combat_attack"],
                default_inputs={
                    "skill_id": "fighting_brawl",
                    "target_actor_id": "__subject__",
                    "damage": "__weapon_damage__",
                    "weapon_item": {
                        "name": "improvised close-combat weapon",
                        "kind": "weapon",
                        "profile": {
                            "skill_id": "fighting_brawl",
                            "damage": {"count": 1, "sides": 3, "modifier": 0},
                            "range": "touch",
                        },
                    },
                    "reason": f"hostile action against {actor.name}",
                    "target_hp": 10,
                },
                parameter_requirements=["target_actor_id", "target_hp", "improvised_weapon"],
                priority=50,
                repeat_policy="always",
            )
        )
    return result
