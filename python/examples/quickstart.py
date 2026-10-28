"""Quickstart. Needs ANTHROPIC_API_KEY or OPENAI_API_KEY in env.

    python examples/quickstart.py
"""
import asyncio

from swarmagents import Agent, TextDelta, ToolCallStart, tool


@tool
def get_weather(city: str) -> dict:
    """Current weather for a city (fake data for the demo)."""
    return {"city": city, "temp_c": 31, "condition": "humid, scattered clouds"}


agent = Agent(
    "You help people plan short trips. Be concise.",
    tools=[get_weather, "time", "math"],
)

# 1. Simplest possible call
print(agent.run("What's the weather in Lagos and what time is it there?"))


# 2. Streaming with events
async def main():
    async for ev in agent.stream("Convert 25 miles to km and tell me the weather in Abuja."):
        if isinstance(ev, TextDelta):
            print(ev.text, end="", flush=True)
        elif isinstance(ev, ToolCallStart):
            print(f"\n[calling {ev.call.name}]")
    print()


asyncio.run(main())
