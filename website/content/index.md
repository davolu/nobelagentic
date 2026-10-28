---
title: Getting started
nav: Getting started
order: 1
---
# Getting started

NobelAgentic is an agent framework with one rule: you should never have to learn more of it than the task needs. Start with one agent. Add tools, MCP servers, handoffs, crews or graphs only when they earn their place.

## Install

Python:

```bash
pip install "nobelagentic[anthropic]"     # or [openai], [all]
```

TypeScript:

```bash
npm install nobelagentic @anthropic-ai/sdk   # or openai
```

Set one API key and you're done — the model is picked from whatever key is present:

```bash
export ANTHROPIC_API_KEY=sk-ant-...    # or OPENAI_API_KEY, GEMINI_API_KEY
```

No key? Run a local model: `model="ollama:llama3.1"`.

## Your first agent

Python:

```python
from nobelagentic import Agent, tool

@tool
def get_weather(city: str) -> str:
    """Current weather for a city."""
    return f"{city}: 31°C, humid"

agent = Agent("You help plan trips", tools=[get_weather, "web", "time"])
print(agent.run("What's the weather in Lagos and what time is it there?"))
```

TypeScript:

```ts
import { Agent, tool, z } from "nobelagentic";

const getWeather = tool({
  name: "get_weather",
  description: "Current weather for a city",
  parameters: z.object({ city: z.string() }),
  execute: ({ city }) => `${city}: 31°C, humid`,
});

const agent = new Agent("You help plan trips", { tools: [getWeather, "web", "time"] });
console.log(await agent.run("What's the weather in Lagos?"));
```

What happened: the model saw your tool's schema (built from the type hints and docstring), decided to call it, the framework ran it, fed the result back, and the model wrote the answer. That loop runs until the model stops calling tools or hits `max_steps`.

## Streaming

`run()` returns the finished result. `stream()` yields events as they happen — text deltas, tool calls, handoffs — so you can render progress live.

```python
async for ev in agent.stream("..."):
    match ev:
        case TextDelta(text): print(text, end="")
        case ToolCallStart(call): print("calling", call.name)
```

## Next

- [Tools](tools.html) — writing your own, and the built-in packs
- [Models](models.html) — choosing and switching providers
- [MCP](mcp.html) — plugging in any MCP server
- [Handoffs](handoffs.html) — routing between agents
- [CLI](cli.html) — run and chat without writing code
