from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from chatrpg.agents.pi_client import PiClient
from chatrpg.config import Settings
from chatrpg.core.ids import new_id
from chatrpg.db.repositories import PostgresIRStore, PostgresSourceStore
from chatrpg.db.session import session_scope
from chatrpg.parsers.structured import PiStructuredExtractor
from chatrpg.systems.coc7e.masks import CampaignAdventureCompiler

app = typer.Typer(help="Compile a source-backed campaign AdventureIR and persist it to Postgres.")
console = Console()


@app.command("run")
def run(document_id: str, adventure_id: str, title: str, limit: int = 300) -> None:
    async def _run() -> None:
        settings = Settings()
        trace_id = new_id("trc")
        async with session_scope(settings) as session:
            source_store = PostgresSourceStore(session)
            blocks = await source_store.list_blocks(document_id=document_id, limit=limit)
            compiler = CampaignAdventureCompiler(PiStructuredExtractor(PiClient(settings)))
            result = await compiler.compile(
                adventure_id=adventure_id,
                title=title,
                blocks=blocks,
                trace_id=trace_id,
            )
            row_id = await PostgresIRStore(session).put_adventure(result.adventure)
        console.print(f"[green]campaign compiled[/green] {row_id} trace={trace_id}")
        if result.issues:
            table = Table(title="AdventureIR validation issues")
            table.add_column("Code")
            table.add_column("Subject")
            table.add_column("Message")
            for issue in result.issues:
                table.add_row(issue.code, issue.subject, issue.message)
            console.print(table)

    asyncio.run(_run())
