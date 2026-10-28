# NobelAgentic

**Agents that get out of your way.** One kernel, three APIs, any model — in Python and TypeScript with the same API.

```python
from nobelagentic import Agent, tool

@tool
def get_weather(city: str) -> str:
    """Current weather for a city."""
    return f"{city}: 31°C, humid"

print(Agent("You help plan trips", tools=[get_weather, "web"]).run("Weather in Lagos?"))
```

```ts
import { Agent, tool, z } from "nobelagentic";

const getWeather = tool({ name: "get_weather", description: "Current weather for a city",
  parameters: z.object({ city: z.string() }), execute: ({ city }) => `${city}: 31°C, humid` });

console.log(await new Agent("You help plan trips", { tools: [getWeather, "web"] }).run("Weather in Lagos?"));
```

| | |
|---|---|
| Install | `pip install nobelagentic` · `npm i nobelagentic` |
| Docs | https://nobelagentic.vercel.app |
| Python package | [`python/`](python/) |
| TypeScript package | [`typescript/`](typescript/) |
| Website + docs source | [`website/`](website/) |

## What's in v0.1

- `@tool` / `tool()` — the schema comes from type hints or a zod object; no JSON schema by hand
- One provider interface — Anthropic natively, plus OpenAI, Gemini, Ollama, Groq, OpenRouter and Together through one OpenAI-compatible adapter; auto-picks a model from your env
- The agent loop — real token streaming, parallel tool calls, tool errors fed back to the model, `max_steps` guard
- Six built-in tool packs (`web` `files` `shell` `time` `math` `data`), lazy-loaded by name
- MCP client with a registry of well-known servers plus your own in `~/.nobelagentic/mcp.json`
- Handoffs between agents
- A CLI: `nobelagentic run | chat | tools list | mcp add`
- Offline test suites in both languages against a scripted fake provider

## Roadmap

v0.2 graph kernel → v0.3 crews, memory, guardrails, tracing → v0.4 MCP server mode, tool registry, 100+ tools. Details in the [docs](website/content/roadmap.md).

## Develop

```bash
cd python && pip install -e ".[all,dev]" && pytest
cd typescript && npm install && npm test && npm run build
cd website && python build.py          # regenerates docs/*.html from content/*.md
```

## Release

Bump the version in `python/pyproject.toml` and `typescript/package.json`, push to `main`. CI publishes whatever version isn't on the registry yet, then tags it and creates a GitHub release. Needs `PYPI_API_TOKEN` and `NPM_TOKEN` as repository secrets.

MIT licensed.
