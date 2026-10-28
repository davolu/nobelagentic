---
title: Handoffs & orchestration
nav: Multi-agent
order: 5
---
# Handoffs & orchestration

Two ways to put agents together, for two different shapes of problem. A **handoff** transfers the conversation — right when one specialist should take over and answer the user directly. An **orchestrator** keeps control — right when one agent should delegate subtasks, collect the results, and combine them.

## Handoffs

A handoff passes the conversation to another agent. It's the seed of the Crew API and is how you build triage, specialists and escalation paths today.

```python
from nobelagentic import Agent

billing = Agent("Handle billing questions. Be precise.", name="billing", tools=["data"])
support = Agent("Handle technical support.", name="support", tools=["web"])

triage = Agent(
    "Route each request to billing or support. Hand off immediately; don't answer yourself.",
    handoffs=[billing, support],
)

result = triage.run("I was charged twice this month")
print(result.agent)    # "billing"
print(result.output)
```

Each handoff target shows up to the model as a tool named `handoff_to_<name>`. When it's called, the target's instructions replace the system prompt, the full conversation carries over, and the loop continues as that agent — with its own tools and model.

## Events

Listen for `Handoff` events to show the user who's answering:

```python
async for ev in triage.stream("..."):
    if isinstance(ev, Handoff):
        print(f"→ now talking to {ev.to_agent}")
```

## Orchestration: agents as tools

`as_tool()` turns any agent into a tool another agent can call. The orchestrator never gives up the conversation — it fires off tasks, gets answers back, and synthesizes:

```python
from nobelagentic import Agent

researcher = Agent("You find facts and cite sources.", name="researcher", tools=["web"])
writer     = Agent("You turn notes into crisp prose.", name="writer")

orchestrator = Agent(
    "You produce short reports. Use the researcher for facts, "
    "the writer for the final text. Combine their work yourself.",
    tools=[researcher.as_tool(), writer.as_tool()],
)

print(orchestrator.run("One paragraph on the state of African fintech"))
```

Same in TypeScript:

```ts
const orchestrator = new Agent("You produce short reports...", {
  tools: [researcher.asTool(), writer.asTool()],
});
```

The sub-agent shows up to the model as a tool named `ask_<name>` (override with `as_tool(name=..., description=...)`). Because sub-agents are ordinary tools, the kernel's parallel tool calls apply: when the orchestrator asks the researcher and the writer for independent things in one step, they run concurrently.

**Choosing between them:** handoff when the *user* should end up talking to the specialist (triage, escalation). Orchestrate when the *agent* needs the specialist's output as an ingredient (research → write → combine).

## Limits

Handoffs are one-way, and an orchestrator sees only a sub-agent's final answer, not its intermediate events. For round-trips, review loops, shared state and resumable multi-step pipelines, use the Graph API (v0.2) or the Crew API (v0.3).
