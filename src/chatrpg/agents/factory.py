from __future__ import annotations

from chatrpg.agents.pi_client import PiClient
from chatrpg.agents.semantic_matcher import PiSemanticMatcher
from chatrpg.config import Settings
from chatrpg.retrieval.fail_closed import FailClosedSemanticMatcher
from chatrpg.retrieval.semantic import SemanticMatcher


def build_semantic_matcher(settings: Settings) -> SemanticMatcher:
    if settings.pi_base_url and settings.pi_api_key:
        return PiSemanticMatcher(PiClient(settings))
    return FailClosedSemanticMatcher()
