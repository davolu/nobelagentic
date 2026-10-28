"""nobelagentic — agents that get out of your way.

    from nobelagentic import Agent, tool

    @tool
    def add(a: int, b: int) -> int:
        \"\"\"Add two numbers.\"\"\"
        return a + b

    print(Agent("You are a calculator.", tools=[add]).run("What is 2+2?"))
"""
__version__ = "0.1.2"

from .agent import Agent
from .tools import Tool, ToolError, tool
from .types import (Event, Handoff, Message, RunEnd, RunResult, StepEnd, TextDelta, ToolCall,
                    ToolCallEnd, ToolCallStart, Usage)
from .providers import Provider, ProviderError

__all__ = [
    "Agent", "tool", "Tool", "ToolError", "Provider", "ProviderError",
    "Message", "ToolCall", "RunResult", "Usage",
    "Event", "TextDelta", "ToolCallStart", "ToolCallEnd", "StepEnd", "Handoff", "RunEnd",
]
