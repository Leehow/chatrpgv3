# chatrpgv3 Project Rules

These rules apply to every change in this repository.

## Core Constitution: Semantic Intent, Not Text Matching

- Do not implement behavior by matching fixed natural-language text, phrases, keywords, substrings, headings, regexes, or a specific language.
- This applies to player intent, GM output, simulated player output, battle reports, rule prose, adventure prose, clues, handouts, and parser/runtime classification.
- Natural-language classification must go through the semantic layer, structured LLM extraction, or another explicit semantic gateway.
- Runtime code may branch on stable structured data only: event types, procedure IDs, schema fields, tool calls, state flags, and validated semantic outputs.
- A different wording, translation, or paraphrase of the same player intent must resolve to the same behavior.
- If the semantic layer cannot determine intent from context, ask for clarification instead of falling back to keyword rules.

## Existing Non-Negotiables

- Postgres only. Do not add SQLite or local database fallbacks.
- Pi/coding-relay is an adapter, not the runtime. The runtime commits dice, procedures, visibility, and state transitions.
- Every AI decision must be traceable through committed events, semantic traces, procedure results, or report-visible evidence.
- User-facing GM text, simulated player text, and battle reports should be Chinese unless the user explicitly requests otherwise.
