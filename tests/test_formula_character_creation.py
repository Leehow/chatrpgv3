from chatrpg.ir.character_template import FormulaBand, FormulaSpec
from chatrpg.runtime.formulas import FormulaEvaluator


def test_formula_evaluator_resolves_arithmetic() -> None:
    result = FormulaEvaluator().evaluate_formula(
        FormulaSpec(id="hp", target_id="hp", expression="floor((con + siz) / 10)", depends_on=["con", "siz"]),
        {"con": 50, "siz": 60},
    )
    assert result.value == 11


def test_formula_evaluator_resolves_banded_value() -> None:
    result = FormulaEvaluator().evaluate_formula(
        FormulaSpec(
            id="build",
            target_id="build",
            kind="banded",
            expression="str + siz",
            bands=[FormulaBand(upper=124, value=0), FormulaBand(upper=164, value=1)],
            default=2,
            depends_on=["str", "siz"],
        ),
        {"str": 70, "siz": 70},
    )
    assert result.value == 1
