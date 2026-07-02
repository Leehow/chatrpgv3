from chatrpg.systems.coc7e.characters import CocInvestigatorFactory, CocInvestigatorProfile


def test_coc7e_investigator_factory_derives_core_resources() -> None:
    profile = CocInvestigatorProfile(
        name="Investigator",
        occupation="antiquarian",
        characteristics={"con": 50, "siz": 60, "pow": 45},
        skills={"spot_hidden": 50},
        luck=40,
    )
    character = CocInvestigatorFactory().create(investigator_id="pc1", profile=profile)
    assert character.resources["hp"] == 11
    assert character.resources["mp"] == 9
    assert character.resources["sanity"] == 45
    assert character.skills["spot_hidden"] == 50
