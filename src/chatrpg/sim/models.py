from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlayerPersona(BaseModel):
    id: str = "sim_human_player"
    name: str = "Simulated Human Player"
    archetype: str = "careful investigator"
    play_style: str = "curious, cautious, clue-driven, and socially pragmatic"
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    table_manners: list[str] = Field(
        default_factory=lambda: [
            "asks clarifying questions when confused",
            "follows visible leads before inventing new ones",
            "backs off from danger when seriously harmed",
            "takes notes like a real player",
        ]
    )
    goals: list[str] = Field(default_factory=lambda: ["understand the mystery", "protect the party", "finish the scenario"])
    limitations: list[str] = Field(
        default_factory=lambda: [
            "does not know hidden Keeper-only facts",
            "does not optimize from future plot knowledge",
            "may make imperfect but reasonable human choices",
        ]
    )


class SimConfig(BaseModel):
    session_id: str
    actor_id: str = "sim_player"
    max_turns: int = Field(default=80, ge=1, le=500)
    min_turns_before_completion: int = Field(default=5, ge=0, le=100)
    report_title: str = "Simulation Battle Report"


class SimTranscriptItem(BaseModel):
    turn_index: int
    player_action: str
    gm_response: str
    committed_event_types: list[str] = Field(default_factory=list)


class SimPlayerObservation(BaseModel):
    session_id: str
    turn_index: int
    persona: PlayerPersona
    transcript: list[SimTranscriptItem] = Field(default_factory=list)
    last_gm_response: str | None = None
    known_objectives: list[str] = Field(default_factory=list)


class SimulatedPlayerAction(BaseModel):
    action: str
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    public_rationale: str
    human_behavior_notes: list[str] = Field(default_factory=list)
    wants_to_stop: bool = False
    stop_reason: str | None = None


class CompletionAssessment(BaseModel):
    status: Literal["continue", "completed", "stuck", "unsafe", "turn_limit"]
    confidence: float = Field(ge=0.0, le=1.0)
    public_rationale: str
    unresolved_goals: list[str] = Field(default_factory=list)


class SimTurnRecord(BaseModel):
    id: str
    run_id: str
    turn_index: int
    player_action: SimulatedPlayerAction
    gm_response: str
    committed_event_types: list[str] = Field(default_factory=list)
    trace_id: str
    completion: CompletionAssessment


class SimRunSummary(BaseModel):
    run_id: str
    session_id: str
    actor_id: str
    status: str
    turns: list[SimTurnRecord] = Field(default_factory=list)
    final_assessment: CompletionAssessment | None = None
    report_markdown: str | None = None
