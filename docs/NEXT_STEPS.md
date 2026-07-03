# Next steps

This PR establishes the runtime foundation and first native CoC kernels. The remaining work is intentionally split into small, reviewable patches.

## Parser compiler

- Implement semantic section grouping from source blocks.
- Use structured LLM extraction for rule tables, statblocks, spells, monsters, and adventure assets.
- Add validator passes for source refs, visibility, clue graph connectivity, and procedure inputs.

## CoC native pack

- Extend combat beyond single attack resolution into round sequencing, dodge/fight-back decisions, armor, major wounds, and healing.
- Extend chase support with locations, hazards, barriers, and participant maneuvers.
- Extend mythos support with tome initial reading, full study, spell learning, spell casting, and artifact effects.
- Add investigator creation and development from the character schema.

## Adventure runtime

- Add semantic clue acquisition routing.
- Add handout reveal events and asset lookup.
- Add chapter/frontier unlock policies.
- Add player-visible narration snapshots that exclude keeper-only and runtime-only facts.

## Play loop

- Turn `trpg play once` into a full REPL.
- Route Pi intent frames through runtime tools.
- Commit proposed events after validation.
- Record every LLM call, semantic match, procedure run, dice roll, and state replay anchor.

## Evals

- Add parser golden tests for CoC Keeper, Masks, Triangle Agency, The Vault, Cyberpunk RED, Homecoming, and Sword World.
- Add deterministic replay tests for skill rolls, SAN, combat attacks, chase rounds, clue discovery, and handout reveal.
