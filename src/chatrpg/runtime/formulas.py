from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from math import ceil, floor
from typing import Any

from chatrpg.ir.character_template import FormulaSpec

_ALLOWED_FUNCTIONS = {"floor": floor, "ceil": ceil, "min": min, "max": max, "round": round}
_ALLOWED_BINOPS = {
    ast.Add: lambda left, right: left + right,
    ast.Sub: lambda left, right: left - right,
    ast.Mult: lambda left, right: left * right,
    ast.Div: lambda left, right: left / right,
    ast.FloorDiv: lambda left, right: left // right,
    ast.Mod: lambda left, right: left % right,
}
_ALLOWED_UNARYOPS = {ast.UAdd: lambda value: value, ast.USub: lambda value: -value}


@dataclass(frozen=True)
class FormulaEvaluation:
    target_id: str
    value: int | str
    formula_id: str
    dependencies: tuple[str, ...]


class FormulaEvaluator:
    def evaluate_formula(self, formula: FormulaSpec, values: Mapping[str, Any]) -> FormulaEvaluation:
        if formula.kind == "banded":
            value = self._evaluate_banded(formula, values)
        else:
            if formula.expression is None:
                raise ValueError(f"Formula {formula.id} does not define an expression")
            value = _eval_arithmetic(formula.expression, values)
            if isinstance(value, float) and value.is_integer():
                value = int(value)
        if not isinstance(value, int | str):
            raise TypeError(f"Formula {formula.id} produced unsupported value type")
        return FormulaEvaluation(
            target_id=formula.target_id,
            value=value,
            formula_id=formula.id,
            dependencies=tuple(formula.depends_on),
        )

    def apply_all(self, formulas: list[FormulaSpec], values: Mapping[str, Any]) -> dict[str, Any]:
        current = dict(values)
        for formula in formulas:
            result = self.evaluate_formula(formula, current)
            current[result.target_id] = result.value
        return current

    @staticmethod
    def _evaluate_banded(formula: FormulaSpec, values: Mapping[str, Any]) -> int | str:
        if formula.expression is None:
            raise ValueError(f"Banded formula {formula.id} requires an expression")
        lookup_value = _eval_arithmetic(formula.expression, values)
        for band in formula.bands:
            if lookup_value <= band.upper:
                return band.value
        if formula.default is None:
            raise ValueError(f"Banded formula {formula.id} has no matching band and no default")
        return formula.default


def _eval_arithmetic(expression: str, values: Mapping[str, Any]) -> int | float:
    tree = ast.parse(expression, mode="eval")
    result = _eval_node(tree.body, values)
    if not isinstance(result, int | float):
        raise TypeError("Formula expression did not evaluate to a number")
    return result


def _eval_node(node: ast.AST, values: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise KeyError(f"Formula variable is missing: {node.id}")
        value = values[node.id]
        if not isinstance(value, int | float):
            raise TypeError(f"Formula variable is not numeric: {node.id}")
        return value
    if isinstance(node, ast.BinOp):
        operator = _ALLOWED_BINOPS.get(type(node.op))
        if operator is None:
            raise ValueError("Formula operator is not allowed")
        return operator(_eval_node(node.left, values), _eval_node(node.right, values))
    if isinstance(node, ast.UnaryOp):
        operator = _ALLOWED_UNARYOPS.get(type(node.op))
        if operator is None:
            raise ValueError("Formula unary operator is not allowed")
        return operator(_eval_node(node.operand, values))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Formula call target is not allowed")
        function = _ALLOWED_FUNCTIONS.get(node.func.id)
        if function is None:
            raise ValueError("Formula function is not allowed")
        return function(*[_eval_node(argument, values) for argument in node.args])
    raise ValueError("Formula expression contains unsupported syntax")
