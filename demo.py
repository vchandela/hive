"""Demo: ReAct agent loop that optimizes Hive retrieval configs.

Runs an LLM agent (GPT-4o) that:
1. Evaluates the current config (discovers low nUDCG, distractors)
2. Reasons about what's wrong
3. Writes an improved config
4. Validates and re-evaluates
5. Deploys the best config

Requires OPENAI_API_KEY environment variable.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

WORKSPACE = "workspace"
MAX_ITERATIONS = 8

SYSTEM_PROMPT = """\
You are a retrieval optimization agent. You have access to Hive, a search engine
with verifiable feedback loops. Your goal is to improve search quality by
iterating on retrieval configs.

CURRENT STATE:
- The corpus is already indexed (20 documents about "DataStack" analytics platform)
- The starting config is workspace/configs/v1.json (naive: hybrid, top_k=10, no dynamic-k, no filters, no distraction detection)
- Golden eval set is at workspace/evals/golden.json (5 queries with labeled relevant/distractor docs)

YOUR STRATEGY:
1. First, evaluate the current config to see how it scores
2. Run some queries to understand what's going wrong
3. Write an improved config (v2) that addresses the issues
4. Validate the new config, then evaluate it
5. If it's better, deploy it. If not, iterate.
6. Try to get nUDCG above 0.6 and eliminate distractors

KEY INSIGHTS:
- FAQ documents are designed distractors (share keywords with api-docs but answer different questions)
- Filtering by category (exclude "faqs") can eliminate distractors
- Dynamic-k with gap-based cutoff stops retrieving when quality drops
- Distraction detection flags results where BM25 and vector rankings disagree

AVAILABLE CONFIGS:
You can write new configs to workspace/configs/v2.json, v3.json, etc.
Configs must have: name, collection, retrieval (method, top_k, rrf_k),
dynamic_k (enabled, gap_threshold_factor, min_results, max_results),
filters (category: [...] or empty), distraction_detection (enabled, disagreement_threshold).

When you are satisfied with the results, deploy the best config and stop.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "hive_evaluate",
            "description": "Evaluate a retrieval config against the golden eval set. Returns per-query nUDCG, precision, and distractor counts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "config_path": {"type": "string", "description": "Path to config JSON file"},
                },
                "required": ["config_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hive_query",
            "description": "Run a search query with a given config. Returns ranked results with scores and distraction flags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "config_path": {"type": "string", "description": "Path to config JSON file"},
                    "query": {"type": "string", "description": "Search query string"},
                },
                "required": ["config_path", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hive_validate",
            "description": "Validate a config for syntactic and semantic errors. Returns pass/fail with error messages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "config_path": {"type": "string", "description": "Path to config JSON file"},
                },
                "required": ["config_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hive_compare",
            "description": "Compare two configs side-by-side on the golden eval set. Shows per-query deltas and config diff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "config_a": {"type": "string", "description": "Path to first config"},
                    "config_b": {"type": "string", "description": "Path to second config"},
                },
                "required": ["config_a", "config_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hive_deploy",
            "description": "Deploy a config as the active config. Will refuse if nUDCG regresses vs the currently active config.",
            "parameters": {
                "type": "object",
                "properties": {
                    "config_path": {"type": "string", "description": "Path to config to deploy"},
                },
                "required": ["config_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_config",
            "description": "Write a new retrieval config JSON file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write (e.g., workspace/configs/v2.json)"},
                    "content": {"type": "string", "description": "JSON string content of the config"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
        },
    },
]


def _run_hive(args: list[str]) -> str:
    """Run a hive CLI command and capture output."""
    result = subprocess.run(
        [sys.executable, "hive.py"] + args,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout
    if result.stderr:
        output += "\n" + result.stderr
    return output[:4000]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if name == "hive_evaluate":
            return _run_hive(["evaluate", arguments["config_path"]])
        elif name == "hive_query":
            return _run_hive(["query", arguments["config_path"], "--q", arguments["query"]])
        elif name == "hive_validate":
            return _run_hive(["validate", arguments["config_path"]])
        elif name == "hive_compare":
            return _run_hive(["compare", arguments["config_a"], arguments["config_b"]])
        elif name == "hive_deploy":
            return _run_hive(["deploy", arguments["config_path"]])
        elif name == "write_config":
            path = Path(arguments["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            # Validate JSON before writing
            content = arguments["content"]
            json.loads(content)  # will raise on bad JSON
            path.write_text(content)
            return f"Successfully wrote config to {path}"
        elif name == "read_file":
            path = Path(arguments["path"])
            if not path.exists():
                return f"File not found: {path}"
            return path.read_text()[:4000]
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def run_demo():
    """Run the agent demo loop."""
    try:
        import openai
    except ImportError:
        console.print("[red]Error: openai package is required. pip install openai[/red]")
        return

    if not os.environ.get("OPENAI_API_KEY"):
        console.print("[red]Error: OPENAI_API_KEY environment variable is required[/red]")
        return

    # Pre-step: ensure index exists
    console.print(Panel("[bold blue]Pre-step: Indexing corpus...[/bold blue]"))
    index_output = _run_hive([
        "index", "workspace/collections/knowledge-base.json",
        "--force", "--no-embeddings",
    ])
    console.print(index_output)

    # Initialize agent
    client = openai.OpenAI()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    console.print(Panel(
        "[bold green]Starting Hive Optimization Agent[/bold green]\n"
        f"Model: gpt-4o | Max iterations: {MAX_ITERATIONS}",
        border_style="green",
    ))

    deployed = False

    for iteration in range(1, MAX_ITERATIONS + 1):
        console.print(f"\n[bold]━━━ Iteration {iteration}/{MAX_ITERATIONS} ━━━[/bold]\n")

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except openai.APIError as e:
            console.print(f"[red]API error: {e}. Retrying...[/red]")
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
            except openai.APIError as e2:
                console.print(f"[red]Retry failed: {e2}. Stopping.[/red]")
                break

        msg = response.choices[0].message

        # Display agent reasoning
        if msg.content:
            console.print(Panel(msg.content, title="Agent Reasoning", border_style="cyan"))

        messages.append(msg)

        tool_calls = msg.tool_calls or []

        if not tool_calls:
            console.print("[dim]Agent returned text only, no tool calls. Ending loop.[/dim]")
            break

        for tc in tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)

            console.print(f"  [bold yellow]→ {fn_name}[/bold yellow]({json.dumps(fn_args, indent=2)[:200]})")

            result = execute_tool(fn_name, fn_args)

            console.print(Panel(result[:1500], title=f"Result: {fn_name}", border_style="dim"))

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        if any(tc.function.name == "hive_deploy" for tc in tool_calls):
            deployed = True
            break

    # Summary
    console.print("\n")
    if deployed:
        console.print(Panel(
            "[bold green]Demo complete![/bold green]\n"
            "The agent successfully optimized the retrieval config through\n"
            "the evaluate → reason → improve → deploy feedback loop.",
            border_style="green",
            title="Summary",
        ))
    else:
        console.print(Panel(
            f"[bold yellow]Demo ended after {MAX_ITERATIONS} iterations without deploying.[/bold yellow]\n"
            "The agent may need more iterations or manual guidance.",
            border_style="yellow",
            title="Summary",
        ))


if __name__ == "__main__":
    run_demo()
