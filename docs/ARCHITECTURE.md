# Architecture

`chatrpgv3` is a source-grounded TRPG runtime. Pi and other LLM adapters may interpret player language, propose semantic matches, and narrate committed results, but deterministic runtime services own dice, procedure settlement, visibility, assets, and state transitions.

```text
CLI / future UI
  -> PlayEngine
  -> WorkflowEngine
  -> AgentLoopEngine
       -> IntentFrame from Pi
       -> SceneFrame from Runtime state + AdventureIR
       -> MechanicTriggerJudge via SemanticMatcher
       -> ParameterResolver / Asset Synthesizer
       -> native Rules Executor
       -> Event replay
  -> Postgres event/source/IR store
  -> Narrator from committed visible facts
```

## Runtime boundary

Pi does not mutate session state. It can propose intent frames, semantic classifications, source-backed extractions, and narration. Runtime services own the authoritative state transition through committed domain events.

## Parser boundary

Rulebook and adventure parsers consume `SourceBlock` evidence and call `SemanticMatcher` for classification or extraction. They must not inspect source prose through literal keywords, substring checks, exact headings, or regular expressions.

## Mechanic adjudication boundary

The GM loop separates fiction from rules:

```text
PlayerInput
  -> IntentFrame
  -> ActionFrame
  -> SceneFrame
  -> MechanicTriggerJudge
  -> MechanicPlan
  -> ParameterResolver
  -> RuntimeActorCreated / RuntimeItemCreated when needed
  -> native procedure events such as AttackResolved or SanityRollResolved
  -> NarrationRequest
```

`MechanicTriggerJudge` never uses literal keyword or substring matching. It receives active `MechanicAffordance` candidates and calls `SemanticMatcher` to decide whether the player action semantically triggers aggression, horror exposure, hazard contact, ambush, chase, social conflict, or another mechanic. This lets scenario-authored affordances and system-level affordances coexist without adding hard-coded text branches.

`ParameterResolver` is responsible for natural-language-to-mechanic binding. If an NPC, weapon, hazard, or sanity stimulus has explicit scenario/rules data, that data should be used. If the fiction requires a parameter that the module did not provide, the resolver may synthesize a temporary runtime asset, but must commit it as an event with provenance. Narration cannot invent these values.

## Storage boundary

Postgres is the only supported database. Source evidence, IR payloads, trace spans, semantic match logs, embeddings, sessions, and domain events are all persisted in Postgres JSONB/vector-backed tables.
