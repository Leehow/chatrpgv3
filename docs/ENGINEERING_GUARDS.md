# Engineering guards

## Postgres-only

The settings layer validates `CHATRPG_DATABASE_URL` before the application starts. The database token guard also scans application and test sources for forbidden local-database dialect tokens.

## Semantic-only text classification

Parser, runtime, and agent code must not use literal text matching to infer rule/adventure semantics, player intent, GM text, simulated player text, battle report meaning, clues, handouts, or other natural-language behavior. This includes substring checks, exact heading checks, regexes, phrase lists, language-specific trigger words, and string methods on prose-bearing variables.

The allowed routes are semantic gateways such as `SemanticMatcher`, structured LLM extraction, or already validated structured outputs such as event types, procedure IDs, schema fields, state flags, and tool calls. If intent cannot be resolved semantically from context, ask for clarification instead of falling back to text matching.

## Why this is strict

The parser and play runtime have to survive OCR variation, translated rulebooks, layout drift, chapter reordering, module-specific prose, paraphrased player utterances, and GM-facing secrecy boundaries. Literal text checks are brittle and create silent parser or gameplay rot.
