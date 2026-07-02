# chatrpgv3

CLI-first implementation scaffold for a source-grounded TRPG runtime.

## Non-negotiable engineering rules

1. **Postgres only.** There is no lightweight local database fallback, no test fallback, and no adapter that silently changes dialects. `CHATRPG_DATABASE_URL` must target Postgres.
2. **No hard-coded text matching.** Parser/runtime/agent code must not classify player intent, GM text, simulated player text, battle reports, rule prose, adventure prose, clues, handouts, or source prose with keyword checks, substring checks, regular expressions, exact heading matches, phrase lists, or a specific language. Use the semantic gateway, structured LLM extraction, or validated structured outputs instead.
3. **Pi is an adapter, not the runtime.** Pi proposes intent, semantic matches, and narration. The runtime commits dice, procedures, visibility, and state transitions.
4. **Every AI decision must be traceable.** Semantic matching requests and results are stored so parser failures can be replayed and diffed.

## Current stack

- Python 3.14.5
- uv-managed project workflow
- Typer + Rich CLI
- Pydantic v2 schemas
- SQLAlchemy 2 + Alembic + psycopg/asyncpg
- Postgres 18 + pgvector
- JSONB source/IR/event payloads
- pgvector HNSW semantic embedding table
- pytest + ruff + mypy

## Quick start

```bash
cp .env.example .env
uv sync --group dev
docker compose up -d postgres
uv run alembic upgrade head
uv run trpg db check
uv run trpg quality guard
uv run pytest
```

## Layout

```text
src/chatrpg/
  agents/        Pi client, main agent, semantic matcher, runtime tool router
  cli/           Typer CLI commands
  config.py      settings with Postgres-only validation
  db/            SQLAlchemy/Postgres models, sessions, repositories
  ingest/        PDF source evidence ingest
  ir/            source-backed ruleset/adventure/session/event schemas
  parsers/       semantic parser and structured extraction contracts
  quality/       static guardrails
  retrieval/     semantic matching and pgvector contracts
  runtime/       deterministic dice/procedure/rules/visibility/knowledge/adventure engines
  systems/       native ruleset packs and system adapters
migrations/      Alembic schema migrations
```

## First CLI targets

```bash
trpg db check
trpg quality guard
trpg session new coc7e --adventure masks
trpg session events <session-id>
trpg session replay <session-id> coc7e masks
trpg play once <session-id> "I inspect the desk"
```

Before merging AI-generated code, run:

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run trpg quality guard
```
