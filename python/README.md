# NobelAgentic (Python)

**Agents that get out of your way.** One kernel, three APIs, any model.

```python
from nobelagentic import Agent, tool

@tool
def get_weather(city: str) -> str:
    """Current weather for a city."""
    return f"{city}: 31°C, humid"

agent = Agent("You help plan trips", tools=[get_weather, "web", "time"])
print(agent.run("What's the weather in Lagos right now?"))
```

No model named → nobelagentic picks one from whatever API key is in your environment.
No schemas written → type hints and the docstring *are* the schema.
Errors tell you what to do, not just what broke.

## Install

```bash
pip install -e ".[all,dev]"      # everything
pip install -e ".[anthropic]"    # or just one provider
```

Set `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` — or run Ollama locally and use `model="ollama:llama3.1"`.

## The three levels

| Level | You write | Who it's for |
|---|---|---|
| `Agent` | one line | 90% of use cases — a model, instructions, tools |
| `Crew` *(v0.3)* | agents + tasks + process | multi-agent, role-based teams |
| `Graph` *(v0.2)* | nodes + edges + state | full control, cycles, human-in-the-loop |

All three compile to the same runtime, so streaming, tracing and checkpoints behave identically everywhere.

## Tools

```python
Agent(tools=[
    my_function,          # any function — sync or async
    "web", "files",       # built-in packs
])
```

Built-in packs (`nobelagentic tools list`): `web` `files` `shell` `time` `math` `data`.
Packs are lazy-loaded; `shell` is opt-in only.

## MCP

```python
Agent(mcp=["github", "postgres"])                       # registry names
Agent(mcp=["https://my-server.example.com/mcp"])        # remote
Agent(mcp=[{"command": "npx", "args": ["-y", "some-mcp-server"]}])
```

`nobelagentic mcp add myserver "npx -y some-mcp-server"` registers one for every project.

## Handoffs

```python
spanish = Agent("You only speak Spanish", name="spanish")
triage  = Agent("Route by language", handoffs=[spanish])
triage.run("Hola!")   # → spanish answers
```

## Orchestration

A handoff transfers the conversation. An orchestrator keeps control — sub-agents become tools it can call, combine and build on:

```python
researcher = Agent("You find facts.", name="researcher", tools=["web"])
writer     = Agent("You write crisp prose.", name="writer")

boss = Agent("Produce short reports. Delegate, then combine.",
             tools=[researcher.as_tool(), writer.as_tool()])
boss.run("One paragraph on African fintech")
```

## Streaming and events

```python
async for ev in agent.stream("..."):
    match ev:
        case TextDelta(text):        print(text, end="")
        case ToolCallStart(call):    print("calling", call.name)
        case RunEnd(output, usage):  print(usage)
```

## Models

```python
Agent(model="claude-opus-5-5")          # prefix → provider
Agent(model="openai:gpt-5")             # explicit
Agent(model="groq:llama-3.3-70b")       # any OpenAI-compatible host
Agent(model=MyProvider())               # bring your own
```

## CLI

```
nobelagentic run "What is 15% of 240?"
nobelagentic chat --tools web,files --mcp github
nobelagentic tools list
nobelagentic mcp list | add
```

## Roadmap

- **v0.1** ✅ provider layer · `@tool` · ReAct loop · streaming · packs · MCP client · handoffs · CLI
- **v0.2** graph kernel (nodes, typed state, checkpoints, resume) · `Agent` re-based on it
- **v0.3** `Crew` API · memory · guardrails · OpenTelemetry tracing · cost tracking
- **v0.4** TypeScript port from the shared spec · MCP *server* mode (`nobelagentic serve --mcp`) · tool registry (`nobelagentic add tool/weather`)

## Layout

```
nobelagentic/
  agent.py        the ReAct loop + handoffs
  tools.py        @tool → JSON schema
  types.py        provider-neutral messages & events
  providers/      anthropic.py, openai_compat.py (OpenAI, Gemini, Ollama, Groq, OpenRouter, Together)
  packs/          built-in tool packs
  mcp.py          MCP client + registry
  cli.py
tests/            runs offline with a scripted FakeProvider
examples/
```

## Run tests

```bash
pytest
```
