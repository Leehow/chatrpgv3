from __future__ import annotations

from chatrpg.ir.character_template import (
    CharacterFieldSpec,
    CharacterTemplate,
    CreationStepSpec,
    FormulaBand,
    FormulaSpec,
)
from chatrpg.ir.source import SourceRef

_DOCUMENT_ID = "coc7e_keeper"


def _ref(page: int) -> SourceRef:
    return SourceRef(document_id=_DOCUMENT_ID, page_start=page, page_end=page, visibility="keeper")


def build_coc7e_investigator_template() -> CharacterTemplate:
    fields = [
        CharacterFieldSpec(id="str", label="STR", kind="characteristic", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="con", label="CON", kind="characteristic", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="siz", label="SIZ", kind="characteristic", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="dex", label="DEX", kind="characteristic", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="app", label="APP", kind="characteristic", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="int", label="INT", kind="characteristic", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="pow", label="POW", kind="characteristic", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="edu", label="EDU", kind="characteristic", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="luck", label="Luck", kind="resource", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="hp", label="Hit Points", kind="resource", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="mp", label="Magic Points", kind="resource", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="sanity", label="Sanity", kind="resource", minimum=0, maximum=99, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="move", label="Move Rate", kind="derived", minimum=0, maximum=20, source_refs=[_ref(34)]),
        CharacterFieldSpec(id="damage_bonus", label="Damage Bonus", kind="derived", source_refs=[_ref(33)]),
        CharacterFieldSpec(id="build", label="Build", kind="derived", source_refs=[_ref(33)]),
        CharacterFieldSpec(id="personal_interest_points", label="Personal Interest Points", kind="derived", source_refs=[_ref(36)]),
    ]
    formulas = [
        FormulaSpec(id="coc7e.hp", target_id="hp", expression="floor((con + siz) / 10)", depends_on=["con", "siz"], source_refs=[_ref(34)]),
        FormulaSpec(id="coc7e.mp", target_id="mp", expression="floor(pow / 5)", depends_on=["pow"], source_refs=[_ref(34)]),
        FormulaSpec(id="coc7e.sanity", target_id="sanity", expression="min(99, pow)", depends_on=["pow"], source_refs=[_ref(34)]),
        FormulaSpec(id="coc7e.personal_interest_points", target_id="personal_interest_points", expression="int * 2", depends_on=["int"], source_refs=[_ref(36)]),
        FormulaSpec(
            id="coc7e.damage_bonus",
            target_id="damage_bonus",
            kind="banded",
            expression="str + siz",
            bands=[
                FormulaBand(upper=64, value="-2"),
                FormulaBand(upper=84, value="-1"),
                FormulaBand(upper=124, value="0"),
                FormulaBand(upper=164, value="+1D4"),
                FormulaBand(upper=204, value="+1D6"),
                FormulaBand(upper=284, value="+2D6"),
                FormulaBand(upper=364, value="+3D6"),
                FormulaBand(upper=444, value="+4D6"),
                FormulaBand(upper=524, value="+5D6"),
            ],
            default="+5D6+",
            depends_on=["str", "siz"],
            source_refs=[_ref(33)],
        ),
        FormulaSpec(
            id="coc7e.build",
            target_id="build",
            kind="banded",
            expression="str + siz",
            bands=[
                FormulaBand(upper=64, value=-2),
                FormulaBand(upper=84, value=-1),
                FormulaBand(upper=124, value=0),
                FormulaBand(upper=164, value=1),
                FormulaBand(upper=204, value=2),
                FormulaBand(upper=284, value=3),
                FormulaBand(upper=364, value=4),
                FormulaBand(upper=444, value=5),
                FormulaBand(upper=524, value=6),
            ],
            default=7,
            depends_on=["str", "siz"],
            source_refs=[_ref(33)],
        ),
    ]
    steps = [
        CreationStepSpec(id="determine_characteristics", label="Determine Characteristics", description="Roll, choose, or allocate STR, CON, SIZ, DEX, APP, INT, POW, and EDU; then apply age modifiers.", required_fields=["str", "con", "siz", "dex", "app", "int", "pow", "edu"], source_refs=[_ref(34)]),
        CreationStepSpec(id="derive_attributes", label="Derived Attributes", description="Calculate HP, MP, SAN, damage bonus, build, Move, Luck, and half/fifth reference values.", formulas_to_apply=[formula.id for formula in formulas], source_refs=[_ref(34)]),
        CreationStepSpec(id="occupation_skills", label="Occupation and Skills", description="Choose occupation, spend occupation points on listed skills and Credit Rating, then spend INT × 2 personal interest points.", required_fields=["occupation"], source_refs=[_ref(36)]),
        CreationStepSpec(id="background", label="Background", description="Add name, age, residence, birthplace, appearance, ideology, significant people, locations, possessions, traits, and optional portrait.", source_refs=[_ref(34)]),
    ]
    return CharacterTemplate(
        id="coc7e.investigator",
        system_id="coc7e",
        label="Call of Cthulhu 7e Investigator",
        fields=fields,
        formulas=formulas,
        creation_steps=steps,
        source_refs=[_ref(34), _ref(36)],
    )
