from __future__ import annotations

from dataclasses import dataclass

from chatrpg.ir.events import DomainEvent
from chatrpg.runtime.dice import DiceEngine, DiceRequest, DiceResult
from chatrpg.runtime.procedure import ProcedureEngine, ProcedureInput, ProcedureRun


@dataclass(frozen=True)
class CommitResult:
    events: tuple[DomainEvent, ...]


class RuntimeToolRouter:
    def __init__(self, *, dice: DiceEngine, procedures: ProcedureEngine) -> None:
        self._dice = dice
        self._procedures = procedures

    def roll_dice(self, request: DiceRequest, *, reason: str) -> DiceResult:
        return self._dice.roll(request, reason=reason)

    def start_procedure(self, request: ProcedureInput) -> ProcedureRun:
        return self._procedures.start(request)

    def commit_events(self, events: list[DomainEvent]) -> CommitResult:
        return CommitResult(events=tuple(events))
