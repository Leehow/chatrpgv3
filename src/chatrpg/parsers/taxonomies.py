from __future__ import annotations

from chatrpg.retrieval.semantic import SemanticCandidate

RULEBOOK_BLOCK_TAXONOMY = [
    SemanticCandidate(id="core_rule", label="Core rule", description="Normative game mechanic."),
    SemanticCandidate(id="procedure_step", label="Procedure step", description="Step in an executable game procedure."),
    SemanticCandidate(id="exception", label="Exception", description="Specific exception or override."),
    SemanticCandidate(id="example", label="Example", description="Illustrative example rather than a rule."),
    SemanticCandidate(id="table", label="Table", description="Structured data table."),
    SemanticCandidate(id="entity_statblock", label="Entity statblock", description="NPC, creature, vehicle, item, spell, or similar stat data."),
    SemanticCandidate(id="gm_advice", label="GM advice", description="Advice or guidance for the game master."),
    SemanticCandidate(id="flavor", label="Flavor", description="Fiction, lore, prose, or atmospheric text."),
]

ADVENTURE_BLOCK_TAXONOMY = [
    SemanticCandidate(id="scene", label="Scene", description="Playable scene or beat."),
    SemanticCandidate(id="location", label="Location", description="Place the players can visit or investigate."),
    SemanticCandidate(id="npc", label="NPC", description="Non-player character information."),
    SemanticCandidate(id="clue", label="Clue carrier", description="Information that can reveal a truth."),
    SemanticCandidate(id="revelation", label="Revelation", description="Underlying truth that clues point to."),
    SemanticCandidate(id="handout", label="Handout", description="Player-facing prop or document."),
    SemanticCandidate(id="encounter", label="Encounter", description="Conflict, challenge, combat, chase, or hazard."),
    SemanticCandidate(id="keeper_secret", label="Keeper secret", description="Keeper-only information not visible to players."),
]
