from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from chatrpg.agents.factory import build_semantic_matcher
from chatrpg.agents.main_agent import PiMainAgent
from chatrpg.agents.pi_client import PiClient
from chatrpg.config import Settings
from chatrpg.db.repositories import PostgresEventStore, PostgresIRStore, PostgresSemanticTraceStore
from chatrpg.db.session import session_scope
from chatrpg.play import PlayEngine
from chatrpg.sim.models import PlayerPersona, SimConfig
from chatrpg.sim.player import SimulatedPlayerAgent
from chatrpg.sim.recorder import SimulationRecorder
from chatrpg.sim.report import SimulationReportBuilder
from chatrpg.sim.runner import SimulationRunner

app = typer.Typer(help="Run an LLM-simulated human player against the LLM GM.")
console = Console()


@app.command("run")
def run_simulation(
    session_id: str,
    max_turns: int = 80,
    actor: str = "sim_player",
    persona: str = "cautious_investigator",
    report_path: Path | None = None,
) -> None:
    async def _run() -> None:
        settings = Settings()
        selected_persona = _persona_template(persona)
        config = SimConfig(session_id=session_id, actor_id=actor, max_turns=max_turns)
        async with session_scope(settings) as session:
            gm = PlayEngine(
                agent=PiMainAgent(PiClient(settings)),
                event_store=PostgresEventStore(session),
                ir_store=PostgresIRStore(session),
                semantic_trace_store=PostgresSemanticTraceStore(session),
                semantic_matcher=build_semantic_matcher(settings),
            )
            runner = SimulationRunner(
                player=SimulatedPlayerAgent(PiClient(settings)),
                gm=gm,
                recorder=SimulationRecorder(session),
            )
            result = await runner.run(config=config, persona=selected_persona)
        console.print(f"[green]simulation complete[/green] run={result.run_id} status={result.status} turns={len(result.turns)}")
        if report_path is not None and result.report_markdown is not None:
            report_path.write_text(result.report_markdown, encoding="utf-8")
            console.print(f"[green]report written[/green] {report_path}")

    asyncio.run(_run())


@app.command("report")
def export_report(run_id: str, output: Path) -> None:
    async def _run() -> None:
        settings = Settings()
        async with session_scope(settings) as session:
            recorder = SimulationRecorder(session)
            row = await recorder.load_run(run_id=run_id)
            if row is None:
                console.print(f"[red]simulation run not found[/red] {run_id}")
                raise typer.Exit(1)
            turns = await recorder.load_turns(run_id=run_id)
        markdown = SimulationReportBuilder().build_markdown(run=row, turns=turns)
        output.write_text(markdown, encoding="utf-8")
        console.print(f"[green]report written[/green] {output}")

    asyncio.run(_run())


def _persona_template(name: str) -> PlayerPersona:
    if name == "bold_explorer":
        return PlayerPersona(
            id="bold_explorer",
            name="Bold Explorer",
            archetype="decisive pulp adventurer",
            play_style="proactive, brave, experimental, and quick to test dangerous leads",
            risk_tolerance="high",
            goals=["push the plot forward", "protect allies", "confront the central threat"],
        )
    if name == "social_sleuth":
        return PlayerPersona(
            id="social_sleuth",
            name="Social Sleuth",
            archetype="empathetic interview-focused investigator",
            play_style="talks to NPCs, cross-checks stories, and avoids violence when possible",
            risk_tolerance="medium",
            goals=["interview witnesses", "connect motives", "solve the mystery cleanly"],
        )
    return PlayerPersona()
