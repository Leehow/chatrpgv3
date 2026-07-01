from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from chatrpg.core.ids import new_id
from chatrpg.ir.source import SourceRef


class DomainEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("evt"))
    session_id: str
    event_type: str
    actor_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[SourceRef] = Field(default_factory=list)
    trace_id: str
    created_at: datetime | None = None
