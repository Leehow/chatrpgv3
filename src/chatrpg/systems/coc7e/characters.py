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

_QUICK_FIRE_SKILL_VALUES = [70, 60, 60, 50, 50, 50, 40, 40]


class CocInvestigatorProfile(BaseModel):
    name: str
    occupation: str | None = None
    age: int = Field(default=30, ge=15, le=90)
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
        fields: dict[str, int | str] = {**characteristics, "luck": profile.luck, "age": profile.age, "occupation": profile.occupation or ""}
        return CharacterCreationEngine().create(
            template=build_coc7e_investigator_template(),
            request=CharacterCreationInput(
                character_id=investigator_id,
                name=profile.name,
                owner=owner,
                fields=fields,
                skills=profile.skills,
            ),
        )

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
        skills = _quick_fire_skills(occupation=occupation, personal_interest_skills=personal_interest_skills or [])
        profile = CocInvestigatorProfile(
            name=name,
            occupation=occupation,
            age=age,
            characteristics=characteristics,
            skills=skills,
            luck=luck,
        )
        return self.create_with_audit(investigator_id=investigator_id, profile=profile, owner=owner)


def _quick_fire_skills(*, occupation: str, personal_interest_skills: list[str]) -> dict[str, int]:
    selected = _DEFAULT_OCCUPATION_SKILLS.get(occupation, _DEFAULT_OCCUPATION_SKILLS["antiquarian"])
    skills = {skill_id: value for skill_id, value in zip(selected, _QUICK_FIRE_SKILL_VALUES, strict=False)}
    for skill_id in personal_interest_skills[:4]:
        skills[skill_id] = skills.get(skill_id, 0) + 20
    if "cthulhu_mythos" not in skills:
        skills["cthulhu_mythos"] = 0
    return skills


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
