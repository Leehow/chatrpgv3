from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

BANNED_DATABASE_TOKENS = frozenset({"sqli" + "te", "aiosqli" + "te"})
DEFAULT_TEXT_SUFFIXES = frozenset({".py", ".toml", ".yaml", ".yml", ".ini", ".md"})
DEFAULT_EXCLUDED_PARTS = frozenset({".git", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache", "quality"})


@dataclass(frozen=True)
class BannedDatabaseTokenViolation:
    path: Path
    line: int
    token: str


def scan_for_banned_database_tokens(paths: Iterable[Path]) -> list[BannedDatabaseTokenViolation]:
    violations: list[BannedDatabaseTokenViolation] = []
    for path in _iter_text_files(paths):
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            lowered = line.casefold()
            for token in BANNED_DATABASE_TOKENS:
                if token in lowered:
                    violations.append(BannedDatabaseTokenViolation(path=path, line=index, token=token))
    return violations


def _iter_text_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix in DEFAULT_TEXT_SUFFIXES and not _is_excluded(path):
            yield path
        if path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file() and candidate.suffix in DEFAULT_TEXT_SUFFIXES and not _is_excluded(candidate):
                    yield candidate


def _is_excluded(path: Path) -> bool:
    return any(part in DEFAULT_EXCLUDED_PARTS for part in path.parts)
