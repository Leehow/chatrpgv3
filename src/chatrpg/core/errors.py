from __future__ import annotations


class ChatrpgError(Exception):
    """Base exception for application-level failures."""


class SemanticMatcherRequired(ChatrpgError):
    """Raised when prose handling attempts to run without a semantic matcher."""
