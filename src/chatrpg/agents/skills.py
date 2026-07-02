from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SkillCategory = Literal[
    "exploration",
    "social",
    "combat",
    "chase",
    "sanity",
    "recovery",
    "mythos",
    "development",
    "narrative",
]
ToolKind = Literal["procedure", "semantic_match", "retrieval", "narration", "clarification"]


class AgentSkillSpec(BaseModel):
    id: str
    category: SkillCategory
    label: str
    tool_kind: ToolKind
    procedure_id: str | None = None
    required_inputs: list[str] = Field(default_factory=list)
    optional_inputs: list[str] = Field(default_factory=list)
    output_events: list[str] = Field(default_factory=list)
    notes: str = ""


class SkillCall(BaseModel):
    skill_id: str
    tool_kind: ToolKind
    procedure_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""


def build_coc7e_agent_skills() -> list[AgentSkillSpec]:
    return [
        AgentSkillSpec(
            id="coc7e.skill.exploration_check",
            category="exploration",
            label="Exploration or investigation skill check",
            tool_kind="procedure",
            procedure_id="coc7e.skill_roll",
            required_inputs=["skill_id"],
            optional_inputs=["difficulty", "bonus_dice", "penalty_dice", "reason"],
            output_events=["SkillRollResolved"],
            notes="Use for uncertain investigative or physical actions resolved by a character skill or characteristic.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.social_check",
            category="social",
            label="Social pressure or interpersonal skill check",
            tool_kind="procedure",
            procedure_id="coc7e.skill_roll",
            required_inputs=["skill_id"],
            optional_inputs=["difficulty", "bonus_dice", "penalty_dice", "reason"],
            output_events=["SkillRollResolved"],
            notes="Use for Persuade, Charm, Fast Talk, Intimidate, Psychology, Credit Rating, or similar social actions.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.opposed_check",
            category="combat",
            label="Opposed skill or characteristic roll",
            tool_kind="procedure",
            procedure_id="coc7e.opposed_roll",
            required_inputs=["attacker_target", "defender_target"],
            optional_inputs=["reason"],
            output_events=["OpposedRollResolved"],
            notes="Use when two parties directly contest an action and both sides have targets.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.combat_attack",
            category="combat",
            label="Combat attack and damage settlement",
            tool_kind="procedure",
            procedure_id="coc7e.combat_attack",
            required_inputs=["skill_id", "damage"],
            optional_inputs=["target_actor_id", "target_hp", "armor", "bonus_dice", "penalty_dice", "reason"],
            output_events=["AttackResolved", "CharacterResourceChanged", "CharacterConditionAdded"],
            notes="Use when an attack should be rolled and damage may be applied.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.chase_round",
            category="chase",
            label="Chase order or movement check",
            tool_kind="procedure",
            procedure_id="coc7e.chase_round",
            required_inputs=["participants"],
            optional_inputs=["movement_actor_id", "skill_id", "target", "reason"],
            output_events=["ChaseRoundResolved"],
            notes="Use when pursuit, flight, or closing distance matters more than static combat.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.sanity_check",
            category="sanity",
            label="Sanity roll and insanity condition check",
            tool_kind="procedure",
            procedure_id="coc7e.sanity_roll",
            required_inputs=["success_loss", "failure_loss"],
            optional_inputs=["starting_sanity_for_day", "reason"],
            output_events=["SanityRollResolved", "CharacterResourceChanged", "CharacterConditionAdded"],
            notes="Use when a horror, corpse, Mythos revelation, or traumatic event calls for SAN loss.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.first_aid",
            category="recovery",
            label="First Aid recovery check",
            tool_kind="procedure",
            procedure_id="coc7e.first_aid",
            required_inputs=["target_actor_id"],
            optional_inputs=["skill_id", "healing", "reason"],
            output_events=["FirstAidResolved", "CharacterResourceChanged"],
            notes="Use for immediate emergency treatment after injury.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.medicine",
            category="recovery",
            label="Medicine recovery check",
            tool_kind="procedure",
            procedure_id="coc7e.medicine",
            required_inputs=["target_actor_id"],
            optional_inputs=["skill_id", "healing", "reason"],
            output_events=["MedicineResolved", "CharacterResourceChanged", "CharacterConditionRemoved"],
            notes="Use for longer treatment, stabilization, and recovery support.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.bout_of_madness",
            category="sanity",
            label="Bout of madness table roll",
            tool_kind="procedure",
            procedure_id="coc7e.bout_of_madness",
            required_inputs=[],
            optional_inputs=["mode", "reason"],
            output_events=["BoutOfMadnessResolved", "CharacterConditionAdded"],
            notes="Use after insanity is confirmed and a madness episode must be selected.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.cast_spell",
            category="mythos",
            label="Cast Mythos spell",
            tool_kind="procedure",
            procedure_id="coc7e.cast_spell",
            required_inputs=["mp_cost", "sanity_cost"],
            optional_inputs=["power_roll_target", "reason"],
            output_events=["SpellCastResolved", "CharacterResourceChanged"],
            notes="Use when a known spell is intentionally cast.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.study_tome",
            category="mythos",
            label="Study Mythos tome",
            tool_kind="procedure",
            procedure_id="coc7e.study_tome",
            required_inputs=["title", "weeks_required", "mythos_gain", "sanity_loss"],
            optional_inputs=["reason"],
            output_events=["TomeStudyResolved", "CharacterSkillChanged", "CharacterResourceChanged"],
            notes="Use for deliberate study of a Mythos text.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.development",
            category="development",
            label="Investigator development roll",
            tool_kind="procedure",
            procedure_id="coc7e.investigator_development",
            required_inputs=["skill_id"],
            optional_inputs=["current_value", "reason"],
            output_events=["SkillImprovementResolved", "CharacterSkillChanged"],
            notes="Use in the development phase for checked skill improvement.",
        ),
        AgentSkillSpec(
            id="coc7e.skill.retrieve_context",
            category="narrative",
            label="Retrieve rule or adventure context",
            tool_kind="retrieval",
            required_inputs=["query"],
            output_events=[],
            notes="Use when more source-backed rule or adventure context is needed before choosing a procedure.",
        ),
    ]
