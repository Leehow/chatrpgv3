from __future__ import annotations

from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState, KnownFact, SessionState


class StateReducer:
    def initial(self, *, session_id: str, system_id: str, adventure_id: str | None = None) -> SessionState:
        return SessionState(id=session_id, system_id=system_id, adventure_id=adventure_id)

    def apply(self, state: SessionState, event: DomainEvent) -> SessionState:
        next_state = state.model_copy(deep=True)
        if event.event_type == "WorkflowPhaseEntered":
            phase_id = event.payload.get("phase_id")
            if isinstance(phase_id, str):
                next_state.workflow_phase = phase_id
        if event.event_type == "WorkflowPhaseCompleted":
            phase_id = event.payload.get("phase_id")
            if isinstance(phase_id, str) and phase_id not in next_state.completed_workflow_phases:
                next_state.completed_workflow_phases.append(phase_id)
        if event.event_type == "CharacterCreated":
            character = CharacterState.model_validate(event.payload)
            if self._character_index(next_state, character.id) is None:
                next_state.party.append(character)
        if event.event_type == "CharacterResourceChanged":
            actor_id = event.actor_id
            resource_id = event.payload.get("resource_id")
            delta = event.payload.get("delta")
            if isinstance(actor_id, str) and isinstance(resource_id, str) and isinstance(delta, int):
                index = self._character_index(next_state, actor_id)
                if index is not None:
                    current = next_state.party[index].resources.get(resource_id, 0)
                    next_state.party[index].resources[resource_id] = current + delta
        if event.event_type == "CharacterSkillChanged":
            actor_id = event.actor_id
            skill_id = event.payload.get("skill_id")
            delta = event.payload.get("delta")
            value = event.payload.get("value")
            if isinstance(actor_id, str) and isinstance(skill_id, str):
                index = self._character_index(next_state, actor_id)
                if index is not None:
                    if isinstance(value, int):
                        next_state.party[index].skills[skill_id] = value
                    elif isinstance(delta, int):
                        current = next_state.party[index].skills.get(skill_id, 0)
                        next_state.party[index].skills[skill_id] = current + delta
        if event.event_type == "CharacterConditionAdded":
            actor_id = event.actor_id
            condition = event.payload.get("condition")
            if isinstance(actor_id, str) and isinstance(condition, str):
                index = self._character_index(next_state, actor_id)
                if index is not None and condition not in next_state.party[index].conditions:
                    next_state.party[index].conditions.append(condition)
        if event.event_type == "CharacterConditionRemoved":
            actor_id = event.actor_id
            condition = event.payload.get("condition")
            if isinstance(actor_id, str) and isinstance(condition, str):
                index = self._character_index(next_state, actor_id)
                if index is not None:
                    next_state.party[index].conditions = [
                        item for item in next_state.party[index].conditions if item != condition
                    ]
        if event.event_type == "FactLearned":
            next_state.known_facts.append(KnownFact.model_validate(event.payload))
        if event.event_type == "FrontierUnlocked":
            value = event.payload.get("unit_id")
            if isinstance(value, str) and value not in next_state.unlocked_frontier:
                next_state.unlocked_frontier.append(value)
        if event.event_type == "ClueDiscovered":
            value = event.payload.get("clue_id")
            if isinstance(value, str) and value not in next_state.discovered_clues:
                next_state.discovered_clues.append(value)
        if event.event_type == "HandoutRevealed":
            value = event.payload.get("handout_id")
            if isinstance(value, str) and value not in next_state.revealed_handouts:
                next_state.revealed_handouts.append(value)
        if event.event_type == "ProcedureStarted":
            next_state.active_procedures.append(event.payload)
        if event.event_type == "ProcedureCompleted":
            procedure_id = event.payload.get("procedure_id")
            if isinstance(procedure_id, str):
                next_state.active_procedures = [
                    item
                    for item in next_state.active_procedures
                    if item.get("procedure_id") != procedure_id
                ]
        return next_state

    def replay(self, state: SessionState, events: list[DomainEvent]) -> SessionState:
        current = state
        for event in events:
            current = self.apply(current, event)
        return current

    @staticmethod
    def _character_index(state: SessionState, character_id: str) -> int | None:
        for index, character in enumerate(state.party):
            if character.id == character_id:
                return index
        return None
