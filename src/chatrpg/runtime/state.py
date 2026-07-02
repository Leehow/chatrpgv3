from __future__ import annotations

from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import CharacterState, KnownFact, RuntimeItemState, SessionState


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
            if self._character_index(next_state.party, character.id) is None:
                next_state.party.append(character)
        if event.event_type == "RuntimeActorCreated":
            payload = event.payload.get("actor") if isinstance(event.payload.get("actor"), dict) else event.payload
            character = CharacterState.model_validate(payload)
            if self._character_index(next_state.runtime_actors, character.id) is None:
                next_state.runtime_actors.append(character)
        if event.event_type == "RuntimeItemCreated":
            item_payload = event.payload.get("item") if isinstance(event.payload.get("item"), dict) else event.payload
            item = RuntimeItemState.model_validate(item_payload)
            if self._item_index(next_state.runtime_items, item.id) is None:
                next_state.runtime_items.append(item)
        if event.event_type == "RuntimeItemTransferred":
            item_id = event.payload.get("item_id")
            to_actor_id = event.payload.get("to_actor_id")
            if isinstance(item_id, str) and isinstance(to_actor_id, str):
                index = self._item_index(next_state.runtime_items, item_id)
                if index is not None:
                    next_state.runtime_items[index].owner_actor_id = to_actor_id
        if event.event_type == "CharacterResourceChanged":
            actor_id = event.actor_id
            resource_id = event.payload.get("resource_id")
            delta = event.payload.get("delta")
            if isinstance(actor_id, str) and isinstance(resource_id, str) and isinstance(delta, int):
                character = self._character_mut(next_state, actor_id)
                if character is not None:
                    current = character.resources.get(resource_id, 0)
                    character.resources[resource_id] = current + delta
        if event.event_type == "CharacterSkillChanged":
            actor_id = event.actor_id
            skill_id = event.payload.get("skill_id")
            delta = event.payload.get("delta")
            value = event.payload.get("value")
            if isinstance(actor_id, str) and isinstance(skill_id, str):
                character = self._character_mut(next_state, actor_id)
                if character is not None:
                    if isinstance(value, int):
                        character.skills[skill_id] = value
                    elif isinstance(delta, int):
                        current = character.skills.get(skill_id, 0)
                        character.skills[skill_id] = current + delta
        if event.event_type == "CharacterConditionAdded":
            actor_id = event.actor_id
            condition = event.payload.get("condition")
            if isinstance(actor_id, str) and isinstance(condition, str):
                character = self._character_mut(next_state, actor_id)
                if character is not None and condition not in character.conditions:
                    character.conditions.append(condition)
        if event.event_type == "CharacterConditionRemoved":
            actor_id = event.actor_id
            condition = event.payload.get("condition")
            if isinstance(actor_id, str) and isinstance(condition, str):
                character = self._character_mut(next_state, actor_id)
                if character is not None:
                    character.conditions = [item for item in character.conditions if item != condition]
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
            if isinstance(value, str):
                next_state.pending_clues = [item for item in next_state.pending_clues if item.get("clue_id") != value]
        if event.event_type == "HandoutRevealed":
            value = event.payload.get("handout_id")
            if isinstance(value, str) and value not in next_state.revealed_handouts:
                next_state.revealed_handouts.append(value)
        if event.event_type == "ProcedureStarted":
            next_state.active_procedures.append(event.payload)
        if event.event_type == "ProcedureCompleted":
            procedure_id = event.payload.get("procedure_id")
            if isinstance(procedure_id, str):
                next_state.active_procedures = [item for item in next_state.active_procedures if item.get("procedure_id") != procedure_id]
        if event.event_type in {"SkillRollResolved", "PushedRollResolved"}:
            self._record_pending_luck_decision(next_state, event)
        if event.event_type in {"LuckSpent", "LuckSpendDeclined"}:
            self._resolve_pending_luck_decision(next_state, event)
        if event.event_type == "CluePending":
            self._record_pending_clue(next_state, event)
        if event.event_type == "PendingClueResolved":
            self._resolve_pending_clue(next_state, event)
        return next_state

    def replay(self, state: SessionState, events: list[DomainEvent]) -> SessionState:
        current = state
        for event in events:
            current = self.apply(current, event)
        return current

    @staticmethod
    def _record_pending_luck_decision(state: SessionState, event: DomainEvent) -> None:
        payload = event.payload
        if payload.get("can_spend_luck") is not True or event.actor_id is None:
            return
        target = payload.get("target")
        roll = payload.get("roll")
        difficulty = payload.get("difficulty", "regular")
        if not isinstance(target, int) or not isinstance(roll, int):
            return
        decision = {
            "id": event.id,
            "source_event_id": event.id,
            "kind": "luck_spend",
            "procedure_id": "coc7e.luck_spend",
            "actor_id": event.actor_id,
            "roll": roll,
            "target": target,
            "difficulty": difficulty,
            "luck_to_success": payload.get("luck_to_success"),
            "target_ref": payload.get("target_ref"),
            "reason": payload.get("resolution", {}).get("title") if isinstance(payload.get("resolution"), dict) else None,
        }
        state.pending_decisions = [
            item
            for item in state.pending_decisions
            if item.get("source_event_id") != event.id
            and not (item.get("kind") == "luck_spend" and item.get("actor_id") == event.actor_id)
        ]
        state.pending_decisions.append(decision)

    @staticmethod
    def _resolve_pending_luck_decision(state: SessionState, event: DomainEvent) -> None:
        origin_event_id = event.payload.get("source_event_id")
        if isinstance(origin_event_id, str):
            state.pending_decisions = [item for item in state.pending_decisions if item.get("source_event_id") != origin_event_id]
            return
        actor_id = event.actor_id
        if isinstance(actor_id, str):
            state.pending_decisions = [item for item in state.pending_decisions if not (item.get("kind") == "luck_spend" and item.get("actor_id") == actor_id)]

    @staticmethod
    def _record_pending_clue(state: SessionState, event: DomainEvent) -> None:
        clue_id = event.payload.get("clue_id")
        if not isinstance(clue_id, str):
            return
        state.pending_clues = [item for item in state.pending_clues if item.get("clue_id") != clue_id]
        state.pending_clues.append(dict(event.payload))

    @staticmethod
    def _resolve_pending_clue(state: SessionState, event: DomainEvent) -> None:
        clue_id = event.payload.get("clue_id")
        origin_event_id = event.payload.get("source_event_id")
        state.pending_clues = [
            item
            for item in state.pending_clues
            if not (
                (isinstance(clue_id, str) and item.get("clue_id") == clue_id)
                or (isinstance(origin_event_id, str) and item.get("source_event_id") == origin_event_id)
            )
        ]

    @staticmethod
    def _character_index(characters: list[CharacterState], character_id: str) -> int | None:
        for index, character in enumerate(characters):
            if character.id == character_id:
                return index
        return None

    @staticmethod
    def _item_index(items: list[RuntimeItemState], item_id: str) -> int | None:
        for index, item in enumerate(items):
            if item.id == item_id:
                return index
        return None

    def _character_mut(self, state: SessionState, character_id: str) -> CharacterState | None:
        party_index = self._character_index(state.party, character_id)
        if party_index is not None:
            return state.party[party_index]
        runtime_index = self._character_index(state.runtime_actors, character_id)
        if runtime_index is not None:
            return state.runtime_actors[runtime_index]
        return None
