from __future__ import annotations

from typing import TypeVar

from chatrpg.core.errors import SemanticMatcherRequired

T = TypeVar("T")


def require_semantic_matcher(matcher: T | None, *, purpose: str) -> T:
    if matcher is None:
        raise SemanticMatcherRequired(
            f"semantic matcher is required for {purpose}; literal content matching is forbidden"
        )
    return matcher
