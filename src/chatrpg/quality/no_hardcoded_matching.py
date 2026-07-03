from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROSE_SIGNAL_NAMES = frozenset(
    {
        "block",
        "body",
        "chunk",
        "content",
        "description",
        "heading",
        "paragraph",
        "prose",
        "query",
        "sentence",
        "source",
        "summary",
        "text",
        "title",
    }
)

BANNED_STRING_METHODS = frozenset(
    {
        "find",
        "index",
        "startswith",
        "endswith",
        "removeprefix",
        "removesuffix",
    }
)

BANNED_REGEX_FUNCTIONS = frozenset(
    {
        "search",
        "match",
        "fullmatch",
        "findall",
        "finditer",
        "split",
        "sub",
    }
)

DEFAULT_EXCLUDED_PATH_PARTS = frozenset(
    {
        ".venv",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "migrations",
        "quality",
    }
)


@dataclass(frozen=True)
class TextMatchViolation:
    path: Path
    line: int
    column: int
    reason: str


def scan_python_paths(paths: Iterable[Path]) -> list[TextMatchViolation]:
    violations: list[TextMatchViolation] = []
    for path in _iter_python_files(paths):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        visitor = _HardcodedTextVisitor(path=path)
        visitor.visit(tree)
        violations.extend(visitor.violations)
    return violations


def _iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py" and not _is_excluded(path):
            yield path
        if path.is_dir():
            for candidate in path.rglob("*.py"):
                if not _is_excluded(candidate):
                    yield candidate


def _is_excluded(path: Path) -> bool:
    return any(part in DEFAULT_EXCLUDED_PATH_PARTS for part in path.parts)


class _HardcodedTextVisitor(ast.NodeVisitor):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        self.violations: list[TextMatchViolation] = []

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in BANNED_STRING_METHODS and _looks_like_prose_expr(node.func.value):
                self._add(node, f"Banned prose string method: {node.func.attr}")
            if _is_regex_module_call(node.func) and any(_contains_string_literal(arg) for arg in node.args):
                self._add(node, f"Banned regex prose matcher: re.{node.func.attr}")
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        has_literal = _contains_string_literal(node.left) or any(_contains_string_literal(c) for c in node.comparators)
        has_prose = _looks_like_prose_expr(node.left) or any(_looks_like_prose_expr(c) for c in node.comparators)
        if has_literal and has_prose:
            operator_names = {type(operator).__name__ for operator in node.ops}
            if operator_names.intersection({"In", "NotIn", "Eq", "NotEq"}):
                self._add(node, "Banned hard-coded prose comparison; use SemanticMatcher")
        self.generic_visit(node)

    def _add(self, node: ast.AST, reason: str) -> None:
        self.violations.append(
            TextMatchViolation(
                path=self.path,
                line=getattr(node, "lineno", 0),
                column=getattr(node, "col_offset", 0),
                reason=reason,
            )
        )


def _is_regex_module_call(func: ast.Attribute) -> bool:
    return isinstance(func.value, ast.Name) and func.value.id == "re" and func.attr in BANNED_REGEX_FUNCTIONS


def _contains_string_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, ast.JoinedStr):
        return True
    return any(_contains_string_literal(child) for child in ast.iter_child_nodes(node))


def _looks_like_prose_expr(node: ast.AST) -> bool:
    return any(_name_has_prose_signal(name) for name in _names_in(node))


def _name_has_prose_signal(name: str) -> bool:
    lowered = name.casefold()
    parts = lowered.split("_")
    return lowered in PROSE_SIGNAL_NAMES or any(part in PROSE_SIGNAL_NAMES for part in parts)


def _names_in(node: ast.AST) -> Iterable[str]:
    if isinstance(node, ast.Name):
        yield node.id
    if isinstance(node, ast.Attribute):
        yield node.attr
    for child in ast.iter_child_nodes(node):
        yield from _names_in(child)
