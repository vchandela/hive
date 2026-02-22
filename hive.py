"""Hive CLI — the agent-facing interface to the retrieval engine.

Six commands: validate, index, query, evaluate, compare, deploy.
Uses typer for argument parsing and rich for formatted terminal output.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.evaluator import compare_configs, evaluate_config
from core.indexer import index_collection
from core.searcher import search
from core.store import HiveStore
from core.validator import validate_config

app = typer.Typer(help="Hive: a retrieval engine with verifiable feedback loops.")
console = Console()

WORKSPACE = "workspace"
DEFAULT_GOLDEN = os.path.join(WORKSPACE, "evals", "golden.json")
DEFAULT_DB = "hive.db"


def _get_store() -> HiveStore:
    return HiveStore(DEFAULT_DB)


# ── validate ────────────────────────────────────────────────────────


@app.command()
def validate(config_path: str = typer.Argument(..., help="Path to config JSON")):
    """Check a retrieval config for syntactic and semantic errors."""
    store = _get_store()
    passed, errors = validate_config(config_path, store)
    store.close()

    if passed:
        console.print(
            Panel("[bold green]✓ Validation passed[/bold green]", border_style="green")
        )
    else:
        console.print(
            Panel("[bold red]✗ Validation failed[/bold red]", border_style="red")
        )
        for err in errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(code=1)


# ── index ───────────────────────────────────────────────────────────


@app.command()
def index(
    collection_path: str = typer.Argument(..., help="Path to collection JSON"),
    force: bool = typer.Option(False, "--force", help="Clear and rebuild index"),
    embeddings_cache: str | None = typer.Option(
        None, "--embeddings-cache", help="Path to .npz cache file"
    ),
    no_embeddings: bool = typer.Option(
        False, "--no-embeddings", help="Skip embedding generation"
    ),
):
    """Index documents from a collection into the search engine."""
    store = _get_store()
    with console.status("[bold blue]Indexing documents..."):
        summary = index_collection(
            collection_path,
            store,
            force=force,
            embeddings_cache=embeddings_cache,
            no_embeddings=no_embeddings,
        )
    store.close()

    table = Table(title="Indexing Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_row("Documents", str(summary["documents"]))
    table.add_row("Chunks", str(summary["chunks"]))
    table.add_row("Unique Terms", str(summary["terms"]))
    table.add_row("Embeddings", "skipped" if no_embeddings else "generated")
    console.print(table)


# ── query ───────────────────────────────────────────────────────────


@app.command()
def query(
    config_path: str = typer.Argument(
        None, help="Path to config JSON (default: active config)"
    ),
    q: str = typer.Option("", "--q", help="Search query string"),
):
    """Run a search query and display ranked results."""
    if not q:
        console.print("[red]Error: --q is required[/red]")
        raise typer.Exit(code=1)

    # Resolve config
    active_path = os.path.join(WORKSPACE, "configs", "active.json")
    if config_path is None:
        if os.path.exists(active_path):
            config_path = active_path
        else:
            console.print(
                "[red]Error: no config specified and no active config found[/red]"
            )
            raise typer.Exit(code=1)

    config = json.loads(Path(config_path).read_text())
    store = _get_store()
    results = search(q, config, store)
    store.close()

    # Format output
    console.print(f'\n[bold]Query:[/bold] "{q}"')
    console.print(
        f"[bold]Config:[/bold] {config['name']} | Method: {config['retrieval']['method']} | Top-k: {config['retrieval']['top_k']}"
    )
    console.print()

    table = Table()
    table.add_column("#", style="dim", width=3)
    table.add_column("RRF Score", justify="right", width=10)
    table.add_column("Document", style="cyan", min_width=30)
    table.add_column("Category", width=12)
    table.add_column("Flagged", width=10)

    for i, r in enumerate(results, 1):
        flag_str = (
            f"[red]⚠ {r.disagreement:.2f}[/red]" if r.flagged and r.disagreement else ""
        )
        table.add_row(
            str(i),
            f"{r.score:.4f}",
            r.chunk_id,
            r.category,
            flag_str,
        )

    console.print(table)

    flagged_count = sum(1 for r in results if r.flagged)
    dk_status = "on" if config.get("dynamic_k", {}).get("enabled") else "off"
    console.print(f"\n{len(results)} results returned (dynamic-k: {dk_status})")
    if flagged_count:
        console.print(
            f"[yellow]{flagged_count} result(s) flagged as potential distractor(s)[/yellow]"
        )


# ── evaluate ────────────────────────────────────────────────────────


@app.command()
def evaluate(
    config_path: str = typer.Argument(..., help="Path to config JSON"),
    golden: str = typer.Option(
        DEFAULT_GOLDEN, "--golden", help="Path to golden eval set"
    ),
):
    """Score a config against the golden evaluation set."""
    store = _get_store()
    result = evaluate_config(config_path, golden, store)
    store.close()

    config = json.loads(Path(config_path).read_text())
    console.print(f"\n[bold]Config:[/bold] {config['name']}")
    console.print()

    table = Table(title="Per-Query Results")
    table.add_column("Query", min_width=30)
    table.add_column("nUDCG", justify="right", width=8)
    table.add_column("Precision", justify="right", width=10)
    table.add_column("Distractors", justify="right", width=12)

    for pq in result["per_query"]:
        nudcg_color = (
            "green" if pq["nudcg"] > 0.5 else "yellow" if pq["nudcg"] > 0 else "red"
        )
        dist_color = "green" if pq["distractor_count"] == 0 else "red"
        table.add_row(
            pq["query"],
            f"[{nudcg_color}]{pq['nudcg']:.4f}[/{nudcg_color}]",
            f"{pq['precision_at_k']:.4f}",
            f"[{dist_color}]{pq['distractor_count']}[/{dist_color}]",
        )

    console.print(table)

    agg = result["aggregate"]
    nudcg_color = (
        "green" if agg["nudcg"] > 0.5 else "yellow" if agg["nudcg"] > 0 else "red"
    )
    console.print(
        Panel(
            f"[bold]Mean nUDCG:[/bold] [{nudcg_color}]{agg['nudcg']:.4f}[/{nudcg_color}]  |  "
            f"[bold]Mean Precision:[/bold] {agg['precision']:.4f}  |  "
            f"[bold]Total Distractors:[/bold] {'[red]' if agg['total_distractors'] else '[green]'}"
            f"{agg['total_distractors']}{'[/red]' if agg['total_distractors'] else '[/green]'}",
            title="Aggregate",
        )
    )


# ── compare ─────────────────────────────────────────────────────────


@app.command()
def compare(
    config_a: str = typer.Argument(..., help="Path to first config"),
    config_b: str = typer.Argument(..., help="Path to second config"),
    golden: str = typer.Option(
        DEFAULT_GOLDEN, "--golden", help="Path to golden eval set"
    ),
):
    """Compare two configs side by side on the golden eval set."""
    store = _get_store()
    result = compare_configs(config_a, config_b, golden, store)
    store.close()

    ca = json.loads(Path(config_a).read_text())
    cb = json.loads(Path(config_b).read_text())

    console.print(f"\n[bold]Comparing:[/bold] {ca['name']} vs {cb['name']}")
    console.print()

    table = Table(title="Per-Query Comparison")
    table.add_column("Query", min_width=25)
    table.add_column(f"nUDCG ({ca['name']})", justify="right", width=12)
    table.add_column(f"nUDCG ({cb['name']})", justify="right", width=12)
    table.add_column("Delta", justify="right", width=8)

    for d in result["deltas"]:
        delta_color = "green" if d["delta"] > 0 else "red" if d["delta"] < 0 else "dim"
        delta_sign = "+" if d["delta"] > 0 else ""
        table.add_row(
            d["query"],
            f"{d['nudcg_a']:.4f}",
            f"{d['nudcg_b']:.4f}",
            f"[{delta_color}]{delta_sign}{d['delta']:.4f}[/{delta_color}]",
        )

    console.print(table)

    # Config diff
    if result["config_diff"]:
        diff_table = Table(title="Config Differences")
        diff_table.add_column("Field")
        diff_table.add_column(ca["name"])
        diff_table.add_column(cb["name"])
        for d in result["config_diff"]:
            diff_table.add_row(d["field"], str(d["a"]), str(d["b"]))
        console.print(diff_table)

    ad = result["aggregate_delta"]
    nudcg_color = "green" if ad["nudcg"] > 0 else "red" if ad["nudcg"] < 0 else "dim"
    console.print(
        Panel(
            f"[bold]nUDCG delta:[/bold] [{nudcg_color}]{'+' if ad['nudcg'] > 0 else ''}{ad['nudcg']:.4f}[/{nudcg_color}]  |  "
            f"[bold]Distractor delta:[/bold] {ad['distractors']:+d}",
            title="Aggregate Delta",
        )
    )


# ── deploy ──────────────────────────────────────────────────────────


@app.command()
def deploy(
    config_path: str = typer.Argument(..., help="Path to config to deploy"),
    golden: str = typer.Option(
        DEFAULT_GOLDEN, "--golden", help="Path to golden eval set"
    ),
):
    """Deploy a config as the active config (refuses if nUDCG regresses)."""
    store = _get_store()

    # Evaluate candidate
    with console.status("[bold blue]Evaluating candidate config..."):
        candidate_eval = evaluate_config(config_path, golden, store)
    candidate_nudcg = candidate_eval["aggregate"]["nudcg"]

    candidate_config = json.loads(Path(config_path).read_text())
    console.print(
        f"\n[bold]Candidate:[/bold] {candidate_config['name']} | nUDCG: {candidate_nudcg:.4f}"
    )

    # Check active config
    active_path = os.path.join(WORKSPACE, "configs", "active.json")
    active_nudcg = None

    if os.path.exists(active_path):
        with console.status("[bold blue]Evaluating active config..."):
            active_eval = evaluate_config(active_path, golden, store)
        active_nudcg = active_eval["aggregate"]["nudcg"]
        active_config = json.loads(Path(active_path).read_text())
        console.print(
            f"[bold]Active:[/bold] {active_config['name']} | nUDCG: {active_nudcg:.4f}"
        )

        if candidate_nudcg < active_nudcg:
            console.print(
                Panel(
                    f"[bold red]Deploy BLOCKED[/bold red]: candidate nUDCG ({candidate_nudcg:.4f}) "
                    f"< active nUDCG ({active_nudcg:.4f}).\n"
                    "The system refuses to deploy a config that makes search quality worse.",
                    border_style="red",
                )
            )
            store.close()
            raise typer.Exit(code=1)

    # Deploy: create/update active.json symlink
    active = Path(active_path)
    if active.is_symlink() or active.exists():
        active.unlink()

    config_abs = Path(config_path).resolve()
    active.symlink_to(config_abs)

    # Record in config_versions
    config_id = store.insert_config_version(
        name=candidate_config["name"],
        version=candidate_config.get("version", "1.0"),
        config_json=json.dumps(candidate_config),
    )
    store.mark_deployed(config_id)
    store.close()

    # Summary
    improvement = ""
    if active_nudcg is not None:
        delta = candidate_nudcg - active_nudcg
        improvement = (
            f"  |  Delta: [green]+{delta:.4f}[/green]"
            if delta > 0
            else f"  |  Delta: {delta:.4f}"
        )

    console.print(
        Panel(
            f"[bold green]✓ Deployed successfully[/bold green]\n"
            f"Config: {candidate_config['name']}  |  nUDCG: {candidate_nudcg:.4f}{improvement}\n"
            f"Active config: {active_path}",
            border_style="green",
        )
    )


if __name__ == "__main__":
    app()
