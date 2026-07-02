from __future__ import annotations

from typing import Any

from chatrpg.agents.skills import build_coc7e_agent_skills
from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.state import SessionState
from chatrpg.ir.workflow import WorkflowPhaseSpec
from chatrpg.runtime.adventure import AdventureFrontier
from chatrpg.runtime.narrative import NarrativeRuntime
from chatrpg.runtime.progress import ProgressController
from chatrpg.systems.coc7e.rules_pack import build_coc7e_native_ruleset


def build_intent_context(
    *,
    system_id: str,
    phase: WorkflowPhaseSpec | None,
    state: SessionState,
    adventure: AdventureIR | None,
    frontier: AdventureFrontier | None,
) -> dict[str, Any]:
    progress = ProgressController().snapshot(state=state, adventure=adventure)
    context: dict[str, Any] = {
        "system_id": system_id,
        "workflow_phase": None if phase is None else phase.model_dump(mode="json"),
        "progress": progress.model_dump(mode="json"),
        "narrative_plan": NarrativeRuntime().plan(progress=progress).model_dump(mode="json"),
        "party_status": [_character_context(character) for character in state.party],
        "runtime_actors": [_character_context(character) for character in state.runtime_actors],
        "runtime_items": [item.model_dump(mode="json") for item in state.runtime_items],
        "agent_skills": _agent_skills(system_id),
        "available_procedures": _available_procedures(system_id),
        "pending_decisions": state.pending_decisions,
        "pending_clues": state.pending_clues,
    }
    if adventure is not None and frontier is not None:
        context["adventure_frontier"] = {
            "adventure_id": adventure.adventure_id,
            "title": adventure.title,
            "units": [unit.model_dump(mode="json") for unit in frontier.units],
            "clues": [clue.model_dump(mode="json") for clue in frontier.clues],
            "locations": [
                location.model_dump(mode="json")
                for location in adventure.locations
                if any(unit.id in location.unit_ids for unit in frontier.units)
            ],
            "npcs": [
                npc.model_dump(mode="json")
                for npc in adventure.npcs
                if any(unit.id in npc.unit_ids for unit in frontier.units)
            ],
            "affordances": [affordance.model_dump(mode="json") for affordance in adventure.affordances],
        }
    return context


def procedure_passed(events: list[Any]) -> bool | None:
    for event in events:
        if event.event_type in {"SkillRollResolved", "PushedRollResolved", "LuckSpent"}:
            value = event.payload.get("passed")
            return value if isinstance(value, bool) else None
        if event.event_type == "AttackResolved":
            attack = event.payload.get("attack")
            if isinstance(attack, dict):
                value = attack.get("hit")
                return value if isinstance(value, bool) else None
    return None


def _character_context(character: Any) -> dict[str, Any]:
    return {
        "id": character.id,
        "name": character.name,
        "owner": character.owner,
        "resources": character.resources,
        "traits": character.traits,
        "skills": character.skills,
        "conditions": character.conditions,
    }


def _agent_skills(system_id: str) -> list[dict[str, Any]]:
    if system_id != "coc7e":
        return []
    return [skill.model_dump(mode="json") for skill in build_coc7e_agent_skills()]


def _available_procedures(system_id: str) -> list[dict[str, Any]]:
    if system_id != "coc7e":
        return []
    return [procedure.model_dump(mode="json") for procedure in build_coc7e_native_ruleset().procedures]
