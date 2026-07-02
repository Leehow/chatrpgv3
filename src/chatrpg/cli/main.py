from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from chatrpg import __version__
from chatrpg.config import Settings
from chatrpg.core.ids import new_id
from chatrpg.quality.no_hardcoded_matching import scan_python_paths
from chatrpg.quality.postgres_only import scan_for_banned_database_tokens

DEFAULT_ROOT = Path(".")

app = typer.Typer(help="chatrpgv3 CLI-first runtime")
db_app = typer.Typer(help="Postgres commands")
ingest_app = typer.Typer(help="Source ingest commands")
parse_app = typer.Typer(help="Semantic parser commands")
quality_app = typer.Typer(help="AI-coding guardrails")
session_app = typer.Typer(help="Session commands")
debug_app = typer.Typer(help="Trace and replay commands")
console = Console()


@app.command()
def version() -> None:
    console.print(f"chatrpg {__version__}")


@db_app.command("check")
def db_check() -> None:
    async def _run() -> None:
        from chatrpg.db.repositories import ping_postgres
        from chatrpg.db.session import session_scope

        settings = Settings()
        async with session_scope(settings) as session:
            version_string = await ping_postgres(session)
            console.print("[green]Postgres OK[/green]")
            console.print(version_string)

    asyncio.run(_run())


@ingest_app.command("pdf")
def ingest_pdf_command(file: Path, document_id: str, title: str | None = None) -> None:
    async def _run() -> None:
        from chatrpg.db.repositories import PostgresSourceStore
        from chatrpg.db.session import session_scope
        from chatrpg.ingest import ingest_pdf

        result = ingest_pdf(path=file, document_id=document_id, title=title)
        async with session_scope(Settings()) as session:
            store = PostgresSourceStore(session)
            await store.put_document(result.document)
            await store.put_blocks(result.blocks)
        console.print(f"[green]ingested[/green] {result.document.id}: {len(result.blocks)} blocks")

    asyncio.run(_run())


@parse_app.command("ruleset")
def parse_ruleset(document_id: str, system: str, edition: str, limit: int = 200) -> None:
    async def _run() -> None:
        from chatrpg.agents.factory import build_semantic_matcher
        from chatrpg.db.repositories import PostgresIRStore, PostgresSemanticTraceStore, PostgresSourceStore
        from chatrpg.db.session import session_scope
        from chatrpg.parsers.base import SemanticBlockClassifier
        from chatrpg.parsers.rulebook import RulebookParser
        from chatrpg.retrieval.traced import TracedSemanticMatcher

        settings = Settings()
        trace_id = new_id("trc")
        async with session_scope(settings) as session:
            source_store = PostgresSourceStore(session)
            blocks = await source_store.list_blocks(document_id=document_id, limit=limit)
            matcher = TracedSemanticMatcher(
                matcher=build_semantic_matcher(settings),
                trace_store=PostgresSemanticTraceStore(session),
            )
            parser = RulebookParser(SemanticBlockClassifier(matcher))
            ruleset = await parser.parse_blocks(
                system_id=system,
                edition=edition,
                blocks=blocks,
                trace_id=trace_id,
            )
            row_id = await PostgresIRStore(session).put_ruleset(ruleset)
        console.print(f"[green]ruleset parsed[/green] {row_id} trace={trace_id}")

    asyncio.run(_run())


@parse_app.command("adventure")
def parse_adventure(document_id: str, adventure_id: str, system: str, title: str, limit: int = 200) -> None:
    async def _run() -> None:
        from chatrpg.agents.factory import build_semantic_matcher
        from chatrpg.db.repositories import PostgresIRStore, PostgresSemanticTraceStore, PostgresSourceStore
        from chatrpg.db.session import session_scope
        from chatrpg.parsers.adventure import AdventureParser
        from chatrpg.parsers.base import SemanticBlockClassifier
        from chatrpg.retrieval.traced import TracedSemanticMatcher

        settings = Settings()
        trace_id = new_id("trc")
        async with session_scope(settings) as session:
            source_store = PostgresSourceStore(session)
            blocks = await source_store.list_blocks(document_id=document_id, limit=limit)
            matcher = TracedSemanticMatcher(
                matcher=build_semantic_matcher(settings),
                trace_store=PostgresSemanticTraceStore(session),
            )
            parser = AdventureParser(SemanticBlockClassifier(matcher))
            adventure = await parser.parse_blocks(
                adventure_id=adventure_id,
                system_id=system,
                title=title,
                blocks=blocks,
                trace_id=trace_id,
            )
            row_id = await PostgresIRStore(session).put_adventure(adventure)
        console.print(f"[green]adventure parsed[/green] {row_id} trace={trace_id}")

    asyncio.run(_run())


@quality_app.command("guard")
def quality_guard(root: Path = DEFAULT_ROOT) -> None:
    text_violations = scan_python_paths([root / "src", root / "tests"])
    database_violations = scan_for_banned_database_tokens([root / "src", root / "tests", root / "pyproject.toml"])

    if not text_violations and not database_violations:
        console.print("[green]Quality guards passed[/green]")
        return

    table = Table(title="Quality guard violations")
    table.add_column("Path")
    table.add_column("Line")
    table.add_column("Reason")
    for violation in text_violations:
        table.add_row(str(violation.path), str(violation.line), violation.reason)
    for violation in database_violations:
        table.add_row(str(violation.path), str(violation.line), f"Banned database token: {violation.token}")
    console.print(table)
    raise typer.Exit(1)


@session_app.command("new")
def session_new(system: str, adventure: str | None = None) -> None:
    async def _run() -> None:
        from sqlalchemy import text

        from chatrpg.db.repositories import PostgresEventStore
        from chatrpg.db.session import session_scope

        async with session_scope(Settings()) as session:
            store = PostgresEventStore(session)
            session_id = await store.create_session(system_id=system, adventure_id=adventure)
            await session.execute(text("select 1"))
            console.print(f"[green]created[/green] {session_id}")

    asyncio.run(_run())


@debug_app.command("trace")
def debug_trace(trace_id: str) -> None:
    console.print(f"Trace lookup is wired to Postgres trace_spans. trace_id={trace_id}")


app.add_typer(db_app, name="db")
app.add_typer(ingest_app, name="ingest")
app.add_typer(parse_app, name="parse")
app.add_typer(quality_app, name="quality")
app.add_typer(session_app, name="session")
app.add_typer(debug_app, name="debug")
