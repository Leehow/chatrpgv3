from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from chatrpg.agents.skills import SkillCall


class PlayerInput(BaseModel):
    session_id: str
    actor_id: str | None = None
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class IntentFrame(BaseModel):
    intent: str
    procedure_id: str | None = None
    actor_id: str | None = None
    targets: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    skill_calls: list[SkillCall] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool = False


class NarrationRequest(BaseModel):
    session_id: str
    visible_facts: list[dict[str, object]] = Field(default_factory=list)
    committed_events: list[dict[str, object]] = Field(default_factory=list)
    style: Literal["keeper", "summary", "debug"] = "keeper"


class NarrationResult(BaseModel):
    text: str
    source_refs: list[dict[str, object]] = Field(default_factory=list)
