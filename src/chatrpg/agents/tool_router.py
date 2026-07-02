from __future__ import annotations

from dataclasses import dataclass

from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.state import SessionState
from chatrpg.runtime.adventure import AdventureEngine, AdventureFrontier
from chatrpg.runtime.dice import DiceEngine, DiceRequest, DiceResult
from chatrpg.runtime.handouts import HandoutEngine
from chatrpg.runtime.procedure import ProcedureEngine, ProcedureInput, ProcedureRun


@dataclass(frozen=True)
class CommitResult:
    events: tuple[DomainEvent, ...]


class RuntimeToolRouter:
    def __init__(self, *, dice: DiceEngine, procedures: ProcedureEngine) -> None:
        self._dice = dice
        self._procedures = procedures
        self._adventures = AdventureEngine()
        self._handouts = HandoutEngine()

    def roll_dice(self, request: DiceRequest, *, reason: str) -> DiceResult:
        return self._dice.roll(request, reason=reason)

    def start_procedure(self, request: ProcedureInput) -> ProcedureRun:
        return self._procedures.start(request)

    def get_frontier(self, *, adventure: AdventureIR, state: SessionState) -> AdventureFrontier:
        return self._adventures.frontier(adventure=adventure, state=state)

    def reveal_handout(self, *, session_id: str, handout_id: str, adventure: AdventureIR, trace_id: str) -> CommitResult:
        handout = next((item for item in adventure.handouts if item.id == handout_id), None)
        if handout is None:
            return CommitResult(events=tuple())
        return CommitResult(events=(self._handouts.reveal_event(session_id=session_id, handout=handout, trace_id=trace_id),))

    def commit_events(self, events: list[DomainEvent]) -> CommitResult:
        return CommitResult(events=tuple(events))
