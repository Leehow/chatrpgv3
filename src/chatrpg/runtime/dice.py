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
