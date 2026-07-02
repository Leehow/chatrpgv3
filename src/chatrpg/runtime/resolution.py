from __future__ import annotations

from pydantic import BaseModel, Field

from chatrpg.runtime.dice import DiceRequest, DiceResult


class DiceRollTrace(BaseModel):
    notation: str
    rolls: list[int] = Field(default_factory=list)
    modifier: int = 0
    total: int
    reason: str

    @classmethod
    def from_result(cls, result: DiceResult) -> DiceRollTrace:
        return cls(
            notation=dice_notation(result.request),
            rolls=list(result.rolls),
            modifier=result.request.modifier,
            total=result.total,
            reason=result.reason,
        )


class D100RollTrace(BaseModel):
    notation: str = "1D100"
    value: int = Field(ge=1, le=100)
    unit_die: int = Field(ge=0, le=9)
    tens_dice: list[int] = Field(default_factory=list)
    selected_tens: int = Field(ge=0, le=9)
    bonus_dice: int = Field(default=0, ge=0)
    penalty_dice: int = Field(default=0, ge=0)
    reason: str


class RuleFormulaTrace(BaseModel):
    rule_id: str
    label: str
    formula: str
    inputs: dict[str, int | str] = Field(default_factory=dict)
    output: int | str | bool
    source_refs: list[dict[str, object]] = Field(default_factory=list)


class ResolutionTrace(BaseModel):
    kind: str
    title: str
    rules: list[RuleFormulaTrace] = Field(default_factory=list)
    dice: list[DiceRollTrace | D100RollTrace] = Field(default_factory=list)
    outcome: dict[str, object] = Field(default_factory=dict)

    def summary_lines(self) -> list[str]:
        lines: list[str] = [self.title]
        for rule in self.rules:
            lines.append(f"规则：{rule.label} => {rule.formula}，输入 {rule.inputs}，结果 {rule.output}")
        for dice in self.dice:
            if isinstance(dice, D100RollTrace):
                lines.append(
                    f"骰子：{dice.notation}，个位 {dice.unit_die}，十位候选 {dice.tens_dice}，选中十位 {dice.selected_tens}，结果 {dice.value}"
                )
            else:
                lines.append(f"骰子：{dice.notation}，掷出 {dice.rolls}，修正 {dice.modifier}，总计 {dice.total}")
        lines.append(f"结论：{self.outcome}")
        return lines


def dice_notation(request: DiceRequest) -> str:
    suffix = "" if request.modifier == 0 else f"{request.modifier:+d}"
    return f"{request.count}D{request.sides}{suffix}"
