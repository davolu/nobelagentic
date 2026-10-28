---
title: Roadmap
nav: Roadmap
order: 8
---
# Roadmap

**v0.1 — now.** Provider layer (Anthropic + every OpenAI-compatible host), `@tool`, the ReAct loop with real streaming and parallel tool calls, six tool packs, MCP client with registry, handoffs, CLI. Python and TypeScript with the same API and the same event stream.

**v0.2 — the production agent.** The graph kernel: nodes, edges, typed state, checkpoints and resume. `Agent` is re-based onto it so human-in-the-loop approval ("pause before this tool runs, ask a human") and durable runs come for free. Plus the three things every production user asks for first:

- **Structured outputs** — `Agent(..., output=MyModel)` returns a validated Pydantic model / zod object, not a string.
- **Sessions** — `agent.run(msg, session="user-123")` with pluggable storage. Multi-turn without hand-rolling history.
- **Run limits** — `max_turns`, token and cost budgets per run, tool timeouts, provider retries with backoff.
- **Agent-as-tool** — `other.as_tool()`: the parent stays in control, unlike a handoff.
- Native Gemini adapter.

**v0.3 — crews, memory, and eyes.** `Crew(agents, tasks, process)`. Short-term and vector memory. Knowledge sources — point an agent at your docs (`knowledge=["./docs/*.pdf"]`) and retrieval is handled. Input and output guardrails. Multimodal input (images and files straight into `run()`). Best-in-class observability: OpenTelemetry tracing, per-run cost tracking, and a local trace viewer.

**v0.4 — testable and everywhere.** **Evals**: record a real run once, replay it offline forever — assert on tool calls, outputs and cost in CI. A sandboxed code executor pack (the safe version of `shell`). MCP *server* mode (`nobelagentic serve --mcp`) so your agents are tools for any MCP client. A tool registry: `nobelagentic add tool/weather` pulls a community tool the way `npm` pulls a package. 100+ built-in tools, many as thin wrappers over maintained MCP servers.

**Non-goals, for now.** Voice/realtime pipelines and hosted inference. Plenty of good products do these; we'd rather be the best framework than a mediocre platform.

Suggest or vote on features in [GitHub issues](https://github.com/davolu/nobelagentic/issues).
