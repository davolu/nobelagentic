---
title: Roadmap
nav: Roadmap
order: 7
---
# Roadmap

**v0.1 — now.** Provider layer (Anthropic + every OpenAI-compatible host), `@tool`, the ReAct loop with real streaming and parallel tool calls, six tool packs, MCP client with registry, handoffs, CLI. Python and TypeScript with the same API and the same event stream.

**v0.2 — graph kernel.** Nodes, edges, typed state, checkpoints and resume. `Agent` is re-based onto it so human-in-the-loop and durable runs come for free. Native Gemini adapter.

**v0.3 — crews and memory.** `Crew(agents, tasks, process)`. Short-term and vector memory. Input and output guardrails. OpenTelemetry tracing and cost tracking.

**v0.4 — ecosystem.** MCP server mode (`swarmagents serve --mcp`). A tool registry: `swarmagents add tool/weather` pulls a community tool the way `npm` pulls a package. 100+ built-in tools, many as thin wrappers over maintained MCP servers.

Suggest or vote on features in GitHub issues.
