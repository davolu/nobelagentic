"""MCP client: any MCP server becomes a set of nobelagentic Tools.

    Agent(mcp=["github"])                                   # by registry name
    Agent(mcp=[{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]}])
    Agent(mcp=["https://my-server.example.com/mcp"])        # remote (HTTP)

Registry names map to well-known stdio servers. Users can extend REGISTRY or use ~/.nobelagentic/mcp.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .tools import Tool, ToolError

REGISTRY: dict[str, dict[str, Any]] = {
    "filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]},
    "github": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"],
               "env": ["GITHUB_PERSONAL_ACCESS_TOKEN"]},
    "postgres": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-postgres"], "env": ["DATABASE_URL"]},
    "playwright": {"command": "npx", "args": ["-y", "@playwright/mcp@latest"]},
    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
    "memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]},
    "slack": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-slack"],
              "env": ["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"]},
}

_CONFIG = Path.home() / ".nobelagentic" / "mcp.json"
_sessions: list[Any] = []  # keep sessions alive for the process lifetime


def _resolve_spec(spec: str | dict) -> dict:
    if isinstance(spec, dict):
        return spec
    if spec.startswith("http://") or spec.startswith("https://"):
        return {"url": spec}
    if _CONFIG.exists():
        user = json.loads(_CONFIG.read_text()).get("servers", {})
        if spec in user:
            return user[spec]
    if spec in REGISTRY:
        return REGISTRY[spec]
    raise ToolError(f"Unknown MCP server '{spec}'. Known: {', '.join(REGISTRY)}; or add it with `nobelagentic mcp add`.")


async def connect(spec: str | dict) -> list[Tool]:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:
        raise ToolError("pip install mcp  (or nobelagentic[mcp])") from e
    from contextlib import AsyncExitStack

    cfg = _resolve_spec(spec)
    for var in cfg.get("env", []):
        if not os.environ.get(var):
            raise ToolError(f"MCP server '{spec}' needs env var {var}")

    stack = AsyncExitStack()
    if "url" in cfg:
        from mcp.client.streamable_http import streamablehttp_client
        read, write, _ = await stack.enter_async_context(streamablehttp_client(cfg["url"]))
    else:
        params = StdioServerParameters(command=cfg["command"], args=cfg.get("args", []),
                                       env={**os.environ, **cfg.get("env_values", {})})
        read, write = await stack.enter_async_context(stdio_client(params))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    _sessions.append(stack)

    label = spec if isinstance(spec, str) else cfg.get("command", "mcp")
    tools: list[Tool] = []
    for t in (await session.list_tools()).tools:
        tools.append(_wrap(session, t, label))
    return tools


def _wrap(session: Any, t: Any, label: str) -> Tool:
    async def _call(**kwargs: Any) -> str:
        res = await session.call_tool(t.name, kwargs)
        parts = []
        for c in res.content:
            parts.append(getattr(c, "text", None) or json.dumps(getattr(c, "model_dump", dict)(), default=str))
        out = "\n".join(parts)
        return f"Error: {out}" if getattr(res, "isError", False) else out

    return Tool(name=t.name, description=t.description or t.name,
                parameters=t.inputSchema or {"type": "object", "properties": {}},
                fn=_call, pack=f"mcp:{label}")


def add_server(name: str, cfg: dict) -> None:
    _CONFIG.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(_CONFIG.read_text()) if _CONFIG.exists() else {"servers": {}}
    data.setdefault("servers", {})[name] = cfg
    _CONFIG.write_text(json.dumps(data, indent=2))
