from chatrpg.systems.coc7e import build_coc7e_native_ruleset


def test_coc7e_native_ruleset_contains_core_procedures() -> None:
    ruleset = build_coc7e_native_ruleset()
    procedure_ids = {procedure.id for procedure in ruleset.procedures}
    assert "coc7e.skill_roll" in procedure_ids
    assert "coc7e.sanity_roll" in procedure_ids
    assert "coc7e.luck_spend" in procedure_ids
