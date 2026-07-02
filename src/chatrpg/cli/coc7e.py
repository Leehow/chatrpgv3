from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from chatrpg.config import Settings
from chatrpg.core.ids import new_id
from chatrpg.db.repositories import PostgresEventStore
from chatrpg.db.session import session_scope
from chatrpg.runtime.characters import CharacterEngine
from chatrpg.runtime.dice import DiceEngine
from chatrpg.systems.coc7e.characters import CocInvestigatorFactory

app = typer.Typer(help="Call of Cthulhu 7e character and rules helpers.")
console = Console()


@app.command("create-investigator")
def create_investigator(
    session_id: str,
    name: str,
    occupation: str = "antiquarian",
    age: int = 30,
    owner: str | None = None,
    seed: int | None = None,
) -> None:
    async def _run() -> None:
        character_id = new_id("pc")
        trace_id = new_id("trc")
        result = CocInvestigatorFactory().quick_fire(
            investigator_id=character_id,
            name=name,
            occupation=occupation,
            age=age,
            owner=owner,
            dice=DiceEngine(seed=seed),
            personal_interest_skills=["library_use", "spot_hidden", "listen", "dodge"],
        )
        events = CharacterEngine().create_character_events(
            session_id=session_id,
            character=result.character,
            trace_id=trace_id,
        )
        async with session_scope(Settings()) as session:
            await PostgresEventStore(session).append_many(events)
        console.print(f"[green]investigator created[/green] {result.character.id} trace={trace_id}")
        console.print_json(data=result.character.model_dump(mode="json"))

    asyncio.run(_run())
