# Architecture

`chatrpgv3` starts as a modular monolith because the first bottleneck is correctness and debuggability, not distributed scale.

```text
CLI / future UI
  -> Pi adapter for intent, semantic matching, narration
  -> deterministic runtime for dice, procedures, state, visibility
  -> Postgres event/source/IR store
```

## Runtime boundary

Pi does not mutate session state. It can propose intent frames, semantic classifications, source-backed extractions, and narration. Runtime services own the authoritative state transition through committed domain events.

## Parser boundary

Rulebook and adventure parsers consume `SourceBlock` evidence and call `SemanticMatcher` for classification or extraction. They must not inspect source prose through literal keywords, substring checks, exact headings, or regular expressions.

## Storage boundary

Postgres is the only supported database. Source evidence, IR payloads, trace spans, semantic match logs, embeddings, sessions, and domain events are all persisted in Postgres JSONB/vector-backed tables.
