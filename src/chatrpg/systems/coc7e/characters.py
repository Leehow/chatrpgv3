from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.state import CharacterState
from chatrpg.runtime.character_creation import CharacterCreationEngine, CharacterCreationInput, CharacterCreationResult
from chatrpg.runtime.dice import DiceEngine, DiceRequest
from chatrpg.systems.coc7e.character_template import build_coc7e_investigator_template

_CHARACTERISTIC_IDS = ["str", "con", "siz", "dex", "app", "int", "pow", "edu"]

_DEFAULT_QUICK_FIRE_CHARACTERISTICS = {
    "str": 50,
    "con": 60,
    "siz": 60,
    "dex": 50,
    "app": 50,
    "int": 70,
    "pow": 60,
    "edu": 80,
}

_DEFAULT_OCCUPATION_SKILLS = {
    "antiquarian": ["appraise", "art_craft", "history", "library_use", "other_language", "persuade", "spot_hidden", "occult"],
    "journalist": ["art_craft", "fast_talk", "history", "library_use", "own_language", "persuade", "psychology", "spot_hidden"],
    "private_investigator": ["art_craft_photography", "disguise", "law", "library_use", "listen", "locksmith", "psychology", "spot_hidden"],
    "professor": ["library_use", "other_language", "own_language", "psychology", "science", "history", "persuade", "credit_rating"],
}

_COC7E_BASE_SKILLS = {
    "accounting": 5,
    "anthropology": 1,
    "appraise": 5,
    "archaeology": 1,
    "art_craft": 5,
    "charm": 15,
    "climb": 20,
    "credit_rating": 0,
    "cthulhu_mythos": 0,
    "disguise": 5,
    "dodge": 0,
    "drive_auto": 20,
    "electrical_repair": 10,
    "fast_talk": 5,
    "fighting_brawl": 25,
    "firearms_handgun": 20,
    "firearms_rifle_shotgun": 25,
    "first_aid": 30,
    "history": 5,
    "intimidate": 15,
    "jump": 20,
    "language_own": 0,
    "law": 5,
    "library_use": 20,
    "listen": 20,
    "locksmith": 1,
    "mechanical_repair": 10,
    "medicine": 1,
    "natural_world": 10,
    "navigate": 10,
    "occult": 5,
    "operate_heavy_machinery": 1,
    "persuade": 10,
    "pilot": 1,
    "psychoanalysis": 1,
    "psychology": 10,
    "ride": 5,
    "science": 1,
    "sleight_of_hand": 10,
    "spot_hidden": 25,
    "stealth": 20,
    "survival": 10,
    "swim": 20,
    "throw": 20,
    "track": 10,
}

_QUICK_FIRE_SKILL_VALUES = [70, 60, 60, 50, 50, 50, 40, 40]


class CocInvestigatorProfile(BaseModel):
    name: str
    occupation: str | None = None
    age: int = Field(default=30, ge=15, le=90)
    sex: str | None = None
    gender: str | None = None
    residence: str | None = None
    birthplace: str | None = None
    personal_description: str | None = None
    ideology_beliefs: str | None = None
    significant_people: str | None = None
    meaningful_locations: str | None = None
    treasured_possessions: str | None = None
    traits: str | None = None
    injuries_scars: str | None = None
    phobias_manias: str | None = None
    cash: str | None = None
    spending_level: str | None = None
    assets: str | None = None
    gear: str | None = None
    weapons: str | None = None
    characteristics: dict[str, int] = Field(default_factory=dict)
    skills: dict[str, int] = Field(default_factory=dict)
    luck: int = Field(default=0, ge=0)


class CocInvestigatorFactory:
    def create(self, *, investigator_id: str, profile: CocInvestigatorProfile, owner: str | None = None) -> CharacterState:
        result = self.create_with_audit(investigator_id=investigator_id, profile=profile, owner=owner)
        return result.character

    def create_with_audit(
        self,
        *,
        investigator_id: str,
        profile: CocInvestigatorProfile,
        owner: str | None = None,
    ) -> CharacterCreationResult:
        characteristics = {key: 0 for key in _CHARACTERISTIC_IDS}
        characteristics.update(profile.characteristics)
        skill_values = _complete_skill_values(profile.skills, dex=characteristics["dex"])
        fields: dict[str, int | str] = {
            **characteristics,
            "luck": profile.luck,
            "age": profile.age,
            "occupation": profile.occupation or "",
            "cthulhu_mythos": skill_values.get("cthulhu_mythos", 0),
        }
        for key in _BACKGROUND_FIELD_IDS:
            value = getattr(profile, key)
            if value is not None:
                fields[key] = value
        result = CharacterCreationEngine().create(
            template=build_coc7e_investigator_template(),
            request=CharacterCreationInput(
                character_id=investigator_id,
                name=profile.name,
                owner=owner,
                fields=fields,
                skills=skill_values,
            ),
        )
        character = result.character.model_copy(deep=True)
        character.traits["characteristic_thresholds"] = {
            key: _thresholds(characteristics[key]) for key in _CHARACTERISTIC_IDS
        }
        character.traits["skill_thresholds"] = {key: _thresholds(value) for key, value in skill_values.items()}
        character.traits["sheet_sections"] = [
            "characteristics",
            "derived_attributes",
            "skills",
            "weapons",
            "backstory",
            "cash_assets_gear",
            "wounds_insanity",
            "development",
        ]
        return result.model_copy(update={"character": character}, deep=True)

    def quick_fire(
        self,
        *,
        investigator_id: str,
        name: str,
        dice: DiceEngine,
        occupation: str = "antiquarian",
        age: int = 30,
        owner: str | None = None,
        personal_interest_skills: list[str] | None = None,
    ) -> CharacterCreationResult:
        characteristics = _apply_age_modifiers(dict(_DEFAULT_QUICK_FIRE_CHARACTERISTICS), age=age)
        luck = dice.roll(DiceRequest(count=3, sides=6, modifier=0), reason="coc7e investigator luck").total * 5
        skills = _quick_fire_skills(occupation=occupation, personal_interest_skills=personal_interest_skills or [], dex=characteristics["dex"])
        profile = CocInvestigatorProfile(
            name=name,
            occupation=occupation,
            age=age,
            residence="1920s Boston",
            characteristics=characteristics,
            skills=skills,
            luck=luck,
        )
        return self.create_with_audit(investigator_id=investigator_id, profile=profile, owner=owner)


def _quick_fire_skills(*, occupation: str, personal_interest_skills: list[str], dex: int) -> dict[str, int]:
    skills = _complete_skill_values({}, dex=dex)
    selected = _DEFAULT_OCCUPATION_SKILLS.get(occupation, _DEFAULT_OCCUPATION_SKILLS["antiquarian"])
    for skill_id, value in zip(selected, _QUICK_FIRE_SKILL_VALUES, strict=False):
        skills[skill_id] = max(skills.get(skill_id, 0), value)
    for skill_id in personal_interest_skills[:4]:
        skills[skill_id] = skills.get(skill_id, 0) + 20
    skills["cthulhu_mythos"] = 0
    return skills


def _complete_skill_values(skills: dict[str, int], *, dex: int) -> dict[str, int]:
    completed = dict(_COC7E_BASE_SKILLS)
    completed["dodge"] = max(0, dex // 2)
    completed["language_own"] = max(completed["language_own"], 0)
    completed.update(skills)
    completed.setdefault("cthulhu_mythos", 0)
    return {key: max(0, min(100, value)) for key, value in completed.items()}


def _thresholds(value: int) -> dict[str, int]:
    return {"regular": value, "hard": value // 2, "extreme": value // 5}


def _apply_age_modifiers(characteristics: dict[str, int], *, age: int) -> dict[str, int]:
    if 15 <= age <= 19:
        characteristics["str"] = max(0, characteristics["str"] - 5)
        characteristics["edu"] = max(0, characteristics["edu"] - 5)
    elif 40 <= age <= 49:
        characteristics["dex"] = max(0, characteristics["dex"] - 5)
        characteristics["app"] = max(0, characteristics["app"] - 5)
    elif 50 <= age <= 59:
        characteristics["dex"] = max(0, characteristics["dex"] - 10)
        characteristics["app"] = max(0, characteristics["app"] - 10)
    elif 60 <= age <= 69:
        characteristics["dex"] = max(0, characteristics["dex"] - 20)
        characteristics["app"] = max(0, characteristics["app"] - 15)
    elif 70 <= age <= 79:
        characteristics["dex"] = max(0, characteristics["dex"] - 40)
        characteristics["app"] = max(0, characteristics["app"] - 20)
    elif age >= 80:
        characteristics["dex"] = max(0, characteristics["dex"] - 80)
        characteristics["app"] = max(0, characteristics["app"] - 25)
    return characteristics


_BACKGROUND_FIELD_IDS = [
    "sex",
    "gender",
    "residence",
    "birthplace",
    "personal_description",
    "ideology_beliefs",
    "significant_people",
    "meaningful_locations",
    "treasured_possessions",
    "traits",
    "injuries_scars",
    "phobias_manias",
    "cash",
    "spending_level",
    "assets",
    "gear",
    "weapons",
]
