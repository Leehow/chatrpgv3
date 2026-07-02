from chatrpg.runtime.dice import DiceEngine
from chatrpg.systems.coc7e.characters import CocInvestigatorFactory, CocInvestigatorProfile
from chatrpg.systems.coc7e.character_template import build_coc7e_investigator_template


def test_coc7e_investigator_factory_derives_core_resources() -> None:
    profile = CocInvestigatorProfile(
        name="Investigator",
        occupation="antiquarian",
        characteristics={"con": 50, "siz": 60, "pow": 45},
        skills={"spot_hidden": 50},
        luck=40,
    )
    result = CocInvestigatorFactory().create_with_audit(investigator_id="pc1", profile=profile)
    assert result.character.resources["hp"] == 11
    assert result.character.resources["hp_max"] == 11
    assert result.character.resources["mp"] == 9
    assert result.character.resources["mp_max"] == 9
    assert result.character.resources["sanity"] == 45
    assert result.character.resources["sanity_max"] == 99
    assert result.character.skills["spot_hidden"] == 50
    assert result.character.skills["library_use"] == 20
    assert result.character.traits["characteristic_thresholds"]["pow"] == {"regular": 45, "hard": 22, "extreme": 9}
    assert result.character.traits["skill_thresholds"]["spot_hidden"] == {"regular": 50, "hard": 25, "extreme": 10}
    assert {item.target_id for item in result.audit}.issuperset({"hp", "mp", "sanity", "sanity_max", "move", "damage_bonus", "build"})


def test_coc7e_quick_fire_creation_uses_template_and_luck_roll() -> None:
    result = CocInvestigatorFactory().quick_fire(
        investigator_id="pc1",
        name="Investigator",
        occupation="antiquarian",
        age=30,
        dice=DiceEngine(seed=7),
    )
    assert result.character.resources["hp"] > 0
    assert result.character.resources["luck"] > 0
    assert result.character.traits["personal_interest_points"] == 140
    assert result.character.traits["move"] >= 7
    assert result.character.skills["cthulhu_mythos"] == 0
    assert "weapons" in result.character.traits["sheet_sections"]


def test_coc7e_template_exposes_creation_steps() -> None:
    template = build_coc7e_investigator_template()
    step_ids = {step.id for step in template.creation_steps}
    field_ids = {field.id for field in template.fields}
    assert "determine_characteristics" in step_ids
    assert "derive_attributes" in step_ids
    assert "occupation_skills" in step_ids
    assert {"str_half", "str_fifth", "sanity_max", "cash", "gear", "weapons"}.issubset(field_ids)
