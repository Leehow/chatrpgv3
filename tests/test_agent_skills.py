from chatrpg.agents.contracts import IntentFrame
from chatrpg.agents.skills import SkillCall, build_coc7e_agent_skills
from chatrpg.play.engine import PlayEngine


def test_coc7e_agent_skills_include_runtime_bound_tools() -> None:
    skills = build_coc7e_agent_skills()
    by_id = {skill.id: skill for skill in skills}

    assert by_id["coc7e.skill.combat_attack"].procedure_id == "coc7e.combat_attack"
    assert by_id["coc7e.skill.sanity_check"].procedure_id == "coc7e.sanity_roll"
    assert by_id["coc7e.skill.first_aid"].procedure_id == "coc7e.first_aid"
    assert by_id["coc7e.skill.luck_decline"].procedure_id == "coc7e.luck_decline"


def test_skill_call_can_bind_procedure_intent() -> None:
    intent = IntentFrame(
        intent="调查桌子",
        confidence=0.9,
        skill_calls=[
            SkillCall(
                skill_id="coc7e.skill.exploration_check",
                tool_kind="procedure",
                procedure_id="coc7e.skill_roll",
                inputs={"skill_id": "spot_hidden", "reason": "调查桌子"},
                confidence=0.8,
            )
        ],
    )

    bound = PlayEngine._intent_with_bound_skill_call(intent)

    assert bound.procedure_id == "coc7e.skill_roll"
    assert bound.inputs == {"skill_id": "spot_hidden", "reason": "调查桌子"}
