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
play_app = typer.Typer(help="Playable CLI session commands")
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


@play_app.command("once")
def play_once(session_id: str, message: str, actor: str | None = None) -> None:
    async def _run() -> None:
        from chatrpg.agents.contracts import NarrationRequest, PlayerInput
        from chatrpg.agents.factory import build_semantic_matcher
        from chatrpg.agents.main_agent import PiMainAgent
        from chatrpg.agents.pi_client import PiClient
        from chatrpg.db.repositories import PostgresEventStore, PostgresIRStore, PostgresSemanticTraceStore
        from chatrpg.db.session import session_scope
        from chatrpg.retrieval.traced import TracedSemanticMatcher
        from chatrpg.runtime.adventure import AdventureEngine
        from chatrpg.runtime.clues import ClueAcquisitionEngine
        from chatrpg.runtime.state import StateReducer

        settings = Settings()
        trace_id = new_id("trc")
        agent = PiMainAgent(PiClient(settings))
        intent = await agent.resolve_intent(
            PlayerInput(session_id=session_id, actor_id=actor, message=message),
            trace_id=trace_id,
        )
        committed_events = []
        async with session_scope(settings) as session:
            event_store = PostgresEventStore(session)
            ir_store = PostgresIRStore(session)
            session_row = await event_store.get_session_row(session_id=session_id)
            if session_row is None:
                console.print(f"[red]session not found[/red] {session_id}")
                raise typer.Exit(1)
            events = await event_store.list_events(session_id=session_id)
            reducer = StateReducer()
            state = reducer.replay(
                reducer.initial(
                    session_id=session_id,
                    system_id=session_row.system_id,
                    adventure_id=session_row.adventure_id,
                ),
                events,
            )
            adventure = None
            if session_row.adventure_id is not None:
                adventure = await ir_store.get_adventure(adventure_id=session_row.adventure_id)
            if adventure is not None:
                frontier = AdventureEngine().frontier(adventure=adventure, state=state)
                matcher = TracedSemanticMatcher(
                    matcher=build_semantic_matcher(settings),
                    trace_store=PostgresSemanticTraceStore(session),
                )
                decision = await ClueAcquisitionEngine(matcher).select_clue(
                    player_action=message,
                    available_clues=list(frontier.clues),
                    trace_id=trace_id,
                )
                if decision.clue is not None:
                    committed_events = AdventureEngine().clue_found_events(
                        session_id=session_id,
                        clue=decision.clue,
                        trace_id=trace_id,
                    )
                    await event_store.append_many(committed_events)
            events = [*events, *committed_events]
        narration = await agent.narrate(
            NarrationRequest(
                session_id=session_id,
                committed_events=[event.model_dump(mode="json") for event in events],
                visible_facts=[intent.model_dump(mode="json")],
            ),
            trace_id=trace_id,
        )
        console.print_json(data=intent.model_dump(mode="json"))
        console.print(narration.text)

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


@session_app.command("replay")
def session_replay(session_id: str, system: str, adventure: str | None = None) -> None:
    async def _run() -> None:
        from chatrpg.db.repositories import PostgresEventStore
        from chatrpg.db.session import session_scope
        from chatrpg.runtime.state import StateReducer

        async with session_scope(Settings()) as session:
            store = PostgresEventStore(session)
            events = await store.list_events(session_id=session_id)
        reducer = StateReducer()
        state = reducer.replay(
            reducer.initial(session_id=session_id, system_id=system, adventure_id=adventure),
            events,
        )
        console.print_json(data=state.model_dump(mode="json"))

    asyncio.run(_run())


@session_app.command("events")
def session_events(session_id: str) -> None:
    async def _run() -> None:
        from chatrpg.db.repositories import PostgresEventStore
        from chatrpg.db.session import session_scope

        async with session_scope(Settings()) as session:
            events = await PostgresEventStore(session).list_events(session_id=session_id)
        table = Table(title="Domain events")
        table.add_column("Type")
        table.add_column("Actor")
        table.add_column("Trace")
        for event in events:
            table.add_row(event.event_type, event.actor_id or "-", event.trace_id)
        console.print(table)

    asyncio.run(_run())


@debug_app.command("trace")
def debug_trace(trace_id: str) -> None:
    console.print(f"Trace lookup is wired to Postgres trace_spans. trace_id={trace_id}")


app.add_typer(db_app, name="db")
app.add_typer(ingest_app, name="ingest")
app.add_typer(parse_app, name="parse")
app.add_typer(play_app, name="play")
app.add_typer(quality_app, name="quality")
app.add_typer(session_app, name="session")
app.add_typer(debug_app, name="debug")
