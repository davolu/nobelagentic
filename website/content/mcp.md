---
title: MCP
nav: MCP
order: 4
---
# MCP

Any Model Context Protocol server becomes a set of tools, indistinguishable from native ones.

```python
Agent("...", mcp=["github", "postgres"])
Agent("...", mcp=["https://tools.example.com/mcp"])
Agent("...", mcp=[{"command": "npx", "args": ["-y", "some-mcp-server"]}])
```

## Registry

These names work out of the box:

| Name | Server | Needs |
|---|---|---|
| `filesystem` | `@modelcontextprotocol/server-filesystem` | |
| `github` | `@modelcontextprotocol/server-github` | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| `postgres` | `@modelcontextprotocol/server-postgres` | `DATABASE_URL` |
| `playwright` | `@playwright/mcp` | |
| `fetch` | `mcp-server-fetch` | `uvx` |
| `memory` | `@modelcontextprotocol/server-memory` | |
| `slack` | `@modelcontextprotocol/server-slack` | `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` |

A missing credential fails at agent construction with the variable's name, not halfway through a run.

## Your own servers

```bash
nobelagentic mcp add weather "npx -y weather-mcp --units metric"
nobelagentic mcp add internal https://mcp.internal.example.com/mcp
```

These are saved to `~/.nobelagentic/mcp.json` and available in every project by name.

## Roadmap

MCP *server* mode — exposing an agent or tool pack as an MCP server with `nobelagentic serve --mcp` — is planned for v0.4, so anything you build here plugs into Claude Code, Cursor and other MCP hosts.
