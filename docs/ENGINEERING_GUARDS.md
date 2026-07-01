# Engineering guards

## Postgres-only

The settings layer validates `CHATRPG_DATABASE_URL` before the application starts. The database token guard also scans application and test sources for forbidden local-database dialect tokens.

## Semantic-only text classification

Parser code must not use literal text matching to infer rule/adventure semantics. This includes substring checks, exact heading checks, regexes, and string methods on prose-bearing variables. The only allowed route is `SemanticMatcher`, which is intentionally fail-closed.

## Why this is strict

The parser has to survive OCR variation, translated rulebooks, layout drift, chapter reordering, module-specific prose, and GM-facing secrecy boundaries. Literal text checks are brittle and create silent parser rot.
