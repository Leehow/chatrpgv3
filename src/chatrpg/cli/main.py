from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from chatrpg import __version__
from chatrpg.config import Settings
from chatrpg.quality.no_hardcoded_matching import scan_python_paths
from chatrpg.quality.postgres_only import scan_for_banned_database_tokens

app = typer.Typer(help="chatrpgv3 CLI-first runtime")
db_app = typer.Typer(help="Postgres commands")
quality_app = typer.Typer(help="AI-coding guardrails")
session_app = typer.Typer(help="Session commands")
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


@quality_app.command("guard")
def quality_guard(root: Path = Path(".")) -> None:
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


app.add_typer(db_app, name="db")
app.add_typer(quality_app, name="quality")
app.add_typer(session_app, name="session")
