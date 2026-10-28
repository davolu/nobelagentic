"""nobelagentic CLI.

    nobelagentic run "What's 15% of 240?"         # one-shot with all safe packs
    nobelagentic chat --tools web,files           # interactive
    nobelagentic tools list
    nobelagentic mcp list / add <name> <command> [args...]
"""
from __future__ import annotations

import asyncio
import json
import shlex

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .types import Handoff, RunEnd, TextDelta, ToolCallEnd, ToolCallStart

app = typer.Typer(help="nobelagentic — agents that get out of your way.", no_args_is_help=True)
tools_app = typer.Typer(help="Inspect built-in tool packs.")
mcp_app = typer.Typer(help="Manage MCP servers.")
app.add_typer(tools_app, name="tools")
app.add_typer(mcp_app, name="mcp")
console = Console()

_SAFE_DEFAULT = "web,time,math,data"


def _build(instructions: str, tools: str, model: str | None, mcp: str | None):
    from .agent import Agent
    packs = [p.strip() for p in tools.split(",") if p.strip()]
    servers = [s.strip() for s in (mcp or "").split(",") if s.strip()]
    return Agent(instructions, tools=packs, mcp=servers, model=model)


async def _stream(agent, text: str, history=None):
    async for ev in agent.stream(text, history=history):
        if isinstance(ev, TextDelta):
            console.print(ev.text, end="", highlight=False)
        elif isinstance(ev, ToolCallStart):
            console.print(f"\n[dim]→ {ev.call.name}({json.dumps(ev.call.arguments)[:120]})[/dim]")
        elif isinstance(ev, ToolCallEnd):
            console.print(f"[dim]{'✗' if ev.error else '✓'} {ev.result[:160]!s}[/dim]")
        elif isinstance(ev, Handoff):
            console.print(f"\n[yellow]↪ {ev.from_agent} → {ev.to_agent}[/yellow]")
        elif isinstance(ev, RunEnd):
            console.print(f"\n[dim]{ev.steps} steps · {ev.usage.input_tokens}+{ev.usage.output_tokens} tokens[/dim]")


@app.command()
def run(prompt: str, tools: str = _SAFE_DEFAULT, model: str | None = None, mcp: str | None = None,
        instructions: str = "You are a helpful assistant. Use tools when they help."):
    """Run one prompt and exit."""
    asyncio.run(_stream(_build(instructions, tools, model, mcp), prompt))


@app.command()
def chat(tools: str = _SAFE_DEFAULT, model: str | None = None, mcp: str | None = None,
         instructions: str = "You are a helpful assistant. Use tools when they help."):
    """Interactive chat with memory for the session."""
    from .types import Message
    agent = _build(instructions, tools, model, mcp)
    history: list[Message] = []
    console.print(f"[bold]nobelagentic {__version__}[/bold] · {agent.provider.name}:{agent.provider.model} · tools: {', '.join(agent.tools) or 'none'}")
    while True:
        try:
            text = console.input("[bold cyan]you ›[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            break
        if text.strip() in {"exit", "quit", "/q"}:
            break
        asyncio.run(_stream(agent, text, history))
        result = agent._last_result
        history = [m for m in result.messages if m.role != "system"]
        console.print()


@tools_app.command("list")
def tools_list():
    """Show every built-in tool grouped by pack."""
    from .packs import all_tools
    for pack, tools in all_tools().items():
        t = Table(title=pack, show_header=True, header_style="bold")
        t.add_column("tool"); t.add_column("description")
        for tool in tools:
            t.add_row(tool.name, tool.description)
        console.print(t)


@mcp_app.command("list")
def mcp_list():
    """Show known MCP servers."""
    from .mcp import REGISTRY, _CONFIG
    t = Table(show_header=True, header_style="bold")
    t.add_column("name"); t.add_column("command"); t.add_column("source")
    for n, c in REGISTRY.items():
        t.add_row(n, " ".join([c.get("command", c.get("url", ""))] + c.get("args", [])), "built-in")
    if _CONFIG.exists():
        for n, c in json.loads(_CONFIG.read_text()).get("servers", {}).items():
            t.add_row(n, " ".join([c.get("command", c.get("url", ""))] + c.get("args", [])), "user")
    console.print(t)


@mcp_app.command("add")
def mcp_add(name: str, command: str):
    """Register an MCP server:  nobelagentic mcp add myserver "npx -y some-mcp-server --flag"  (or a URL)."""
    from .mcp import add_server
    if command.startswith("http"):
        add_server(name, {"url": command})
    else:
        parts = shlex.split(command)
        add_server(name, {"command": parts[0], "args": parts[1:]})
    console.print(f"[green]added[/green] {name}")


_SCAFFOLD = {
    "agent.py": '''"""{name} — built with nobelagentic. Run: python agent.py"""
import asyncio

from nobelagentic import Agent, TextDelta, ToolCallStart, tool


@tool
def lookup_order(order_id: str) -> dict:
    """Look up an order by ID (replace with your real data source)."""
    return {{"order_id": order_id, "status": "shipped", "eta_days": 2}}


agent = Agent(
    "You are the support agent for {name}. Be warm and brief.",
    tools=[lookup_order, "time", "math"],
)


async def main() -> None:
    async for ev in agent.stream("Where is order 42?"):
        if isinstance(ev, TextDelta):
            print(ev.text, end="", flush=True)
        elif isinstance(ev, ToolCallStart):
            print(f"\\n[{{ev.call.name}}]")
    print()


if __name__ == "__main__":
    asyncio.run(main())
''',
    "requirements.txt": "nobelagentic[all]>={version}\n",
    ".gitignore": "__pycache__/\n.venv/\n.env\n",
    "README.md": '''# {name}

An agent scaffolded with `nobelagentic new`.

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY / GEMINI_API_KEY
python agent.py
```

Edit `agent.py`: swap `lookup_order` for a real tool, add packs (`"web"`, `"files"`)
or MCP servers (`mcp=["github"]`). Docs: https://nobelagentic.vercel.app/docs
''',
}


@app.command()
def new(name: str):
    """Scaffold a new agent project:  nobelagentic new my-agent."""
    import pathlib
    root = pathlib.Path(name)
    if root.exists():
        console.print(f"[red]error:[/red] '{name}' already exists")
        raise typer.Exit(1)
    root.mkdir(parents=True)
    for fname, content in _SCAFFOLD.items():
        (root / fname).write_text(content.format(name=name, version=__version__))
    console.print(f"[green]created[/green] {name}/ ({', '.join(_SCAFFOLD)})")
    console.print(f"\n  cd {name}")
    console.print("  pip install -r requirements.txt")
    console.print("  export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY")
    console.print("  python agent.py")


@app.command()
def version():
    console.print(__version__)
