from chatrpg.ir.adventure import AdventureIR, ClueCarrier, ContentUnit, HandoutAsset, Revelation
from chatrpg.ir.ruleset import ProcedureSpec, RollSpec, RulesetIR
from chatrpg.ir.validators import AdventureIRValidator, RulesetIRValidator


def test_adventure_validator_accepts_connected_clue_graph() -> None:
    adventure = AdventureIR(
        adventure_id="adv",
        system_id="coc7e",
        title="Case",
        units=[ContentUnit(id="u1", adventure_id="adv", kind="scene", title="Scene", summary="S", visibility="keeper_only")],
        revelations=[Revelation(id="r1", adventure_id="adv", truth_summary="Truth")],
        clues=[ClueCarrier(id="c1", revelation_id="r1", carrier_type="object", unit_id="u1", acquisition="automatic")],
        handouts=[HandoutAsset(id="h1", adventure_id="adv", title="Note", summary="S", reveals=["r1"])],
    )
    assert AdventureIRValidator().validate(adventure) == []


def test_adventure_validator_reports_missing_revelation() -> None:
    adventure = AdventureIR(
        adventure_id="adv",
        system_id="coc7e",
        title="Case",
        units=[ContentUnit(id="u1", adventure_id="adv", kind="scene", title="Scene", summary="S", visibility="keeper_only")],
        clues=[ClueCarrier(id="c1", revelation_id="missing", carrier_type="object", unit_id="u1", acquisition="automatic")],
    )
    issues = AdventureIRValidator().validate(adventure)
    assert {issue.code for issue in issues} == {"missing_clue_revelation"}


def test_ruleset_validator_reports_missing_kernel() -> None:
    ruleset = RulesetIR(
        system_id="demo",
        edition="1",
        procedures=[ProcedureSpec(id="p1", system_id="demo", name="P", rolls=[RollSpec(id="r1", kernel_id="missing")])],
    )
    issues = RulesetIRValidator().validate(ruleset)
    assert {issue.code for issue in issues} == {"missing_roll_kernel"}
