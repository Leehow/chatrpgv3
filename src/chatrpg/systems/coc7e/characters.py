from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.ir.state import CharacterState


class CocInvestigatorProfile(BaseModel):
    name: str
    occupation: str | None = None
    characteristics: dict[str, int] = Field(default_factory=dict)
    skills: dict[str, int] = Field(default_factory=dict)
    luck: int = Field(default=0, ge=0)


class CocInvestigatorFactory:
    def create(self, *, investigator_id: str, profile: CocInvestigatorProfile, owner: str | None = None) -> CharacterState:
        con = profile.characteristics.get("con", 0)
        siz = profile.characteristics.get("siz", 0)
        pow_value = profile.characteristics.get("pow", 0)
        hit_points = max(1, (con + siz) // 10)
        magic_points = max(0, pow_value // 5)
        sanity = max(0, min(99, pow_value))
        return CharacterState(
            id=investigator_id,
            name=profile.name,
            owner=owner,
            resources={"hp": hit_points, "mp": magic_points, "sanity": sanity, "luck": profile.luck},
            traits={"occupation": profile.occupation, **profile.characteristics},
            skills=profile.skills,
        )
