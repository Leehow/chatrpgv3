from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from chatrpg.core.ids import new_id
from chatrpg.ir.events import DomainEvent


@dataclass(frozen=True)
class ProcedureInput:
    procedure_id: str
    session_id: str
    actor_id: str | None
    payload: dict[str, Any]
    trace_id: str


@dataclass(frozen=True)
class ProcedureRun:
    id: str
    procedure_id: str
    status: Literal["started", "waiting", "completed", "errored"]
    proposed_events: tuple[DomainEvent, ...] = field(default_factory=tuple)


class ProcedureEngine:
    def start(self, request: ProcedureInput) -> ProcedureRun:
        event = DomainEvent(
            session_id=request.session_id,
            event_type="ProcedureStarted",
            actor_id=request.actor_id,
            payload={"procedure_id": request.procedure_id, "input": request.payload},
            trace_id=request.trace_id,
        )
        return ProcedureRun(
            id=new_id("prc"),
            procedure_id=request.procedure_id,
            status="started",
            proposed_events=(event,),
        )
