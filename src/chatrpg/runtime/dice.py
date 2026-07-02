from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class DiceRequest:
    count: int
    sides: int
    modifier: int = 0

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("Dice count must be positive")
        if self.sides < 2:
            raise ValueError("Dice sides must be at least 2")


@dataclass(frozen=True)
class DiceResult:
    request: DiceRequest
    rolls: tuple[int, ...]
    total: int
    reason: str


class DiceEngine:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def roll(self, request: DiceRequest, *, reason: str) -> DiceResult:
        rolls = tuple(self._rng.randint(1, request.sides) for _ in range(request.count))
        return DiceResult(request=request, rolls=rolls, total=sum(rolls) + request.modifier, reason=reason)

    def integer(self, *, low: int, high: int, reason: str) -> int:
        if high < low:
            raise ValueError("high must be greater than or equal to low")
        return self._rng.randint(low, high)


def parse_dice_notation(value: str) -> DiceRequest | None:
    notation = "".join(character for character in value.strip().upper() if not character.isspace())
    if "D" not in notation:
        return None
    count_part, rest = notation.split("D", 1)
    if not rest:
        return None
    count = 1 if count_part == "" else _positive_int(count_part)
    modifier = 0
    sides_part = rest
    modifier_index = _modifier_index(rest)
    if modifier_index is not None:
        sides_part = rest[:modifier_index]
        modifier_part = rest[modifier_index:]
        modifier = _signed_int(modifier_part)
        if modifier_part and modifier is None:
            return None
    sides = _positive_int(sides_part)
    if count is None or sides is None:
        return None
    try:
        return DiceRequest(count=count, sides=sides, modifier=modifier)
    except ValueError:
        return None


def _modifier_index(value: str) -> int | None:
    for index, character in enumerate(value):
        if index > 0 and character in {"+", "-"}:
            return index
    return None


def _positive_int(value: str) -> int | None:
    if not value.isdecimal():
        return None
    resolved = int(value)
    return resolved if resolved > 0 else None


def _signed_int(value: str) -> int | None:
    if not value:
        return None
    sign = 1
    digits = value
    if value[0] in {"+", "-"}:
        sign = -1 if value[0] == "-" else 1
        digits = value[1:]
    if not digits.isdecimal():
        return None
    return sign * int(digits)
