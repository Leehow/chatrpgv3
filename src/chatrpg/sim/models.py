from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlayerPersona(BaseModel):
    id: str = "sim_human_player"
    name: str = "模拟人类玩家"
    archetype: str = "谨慎调查员"
    play_style: str = "好奇、谨慎、线索驱动，并且有现实玩家的社交判断"
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    table_manners: list[str] = Field(
        default_factory=lambda: [
            "困惑时会提出澄清问题",
            "先追随可见线索，再提出新假设",
            "受到严重危险时会后退",
            "像真实玩家一样记录要点",
        ]
    )
    goals: list[str] = Field(default_factory=lambda: ["理解谜团", "保护队伍", "完成模组"])
    limitations: list[str] = Field(
        default_factory=lambda: [
            "不知道隐藏的 Keeper 专属事实",
            "不会利用未来剧情知识优化行动",
            "可能做出不完美但合理的人类选择",
        ]
    )


class SimConfig(BaseModel):
    session_id: str
    actor_id: str = "sim_player"
    max_turns: int = Field(default=80, ge=1, le=500)
    min_turns_before_completion: int = Field(default=5, ge=0, le=100)
    report_title: str = "模拟跑团战报"
    auto_create_character: bool = True
    character_name: str = "Harvey Walters"
    character_occupation: str = "antiquarian"
    character_age: int = Field(default=30, ge=15, le=90)
    character_seed: int | None = None


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
    player_visible_state: dict[str, object] = Field(default_factory=dict)


class SimulatedPlayerAction(BaseModel):
    action: str = Field(
        min_length=1,
        max_length=160,
        description="Only the player-visible utterance sent to the GM. One concrete action, normally one or two short sentences.",
    )
    intent: str = Field(default="", max_length=120, description="Private simulator label, not player-visible dialogue.")
    confidence: float = Field(ge=0.0, le=1.0)
    public_rationale: str = Field(
        default="",
        max_length=500,
        description="Private simulator reasoning retained for debugging; not sent to the GM and not rendered in normal battle reports.",
    )
    private_reasoning: str = Field(
        default="",
        max_length=500,
        description="Hidden reasoning used by the simulator to choose the action. Never sent as the player action.",
    )
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
