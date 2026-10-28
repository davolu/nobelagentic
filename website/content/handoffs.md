---
title: Handoffs
nav: Handoffs
order: 5
---
# Handoffs

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

## Limits

Handoffs are one-way. For round-trips, review loops and parallel workers, use the Graph API (v0.2) or the Crew API (v0.3).
