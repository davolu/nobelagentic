"""A scripted fake provider so the loop can be tested without API keys."""
from __future__ import annotations

from nobelagentic.providers.base import Provider
from nobelagentic.types import Message, ModelResponse, ToolCall, Usage


class FakeProvider(Provider):
    """Replays a list of responses. Each item is either a str (final text)
    or a list of (tool_name, args) tuples (tool calls)."""

    name = "fake"

    def __init__(self, script: list):
        super().__init__("fake-1")
        self.script = list(script)
        self.seen: list[list[Message]] = []

    async def complete(self, messages, tools, max_tokens=4096) -> ModelResponse:
        self.seen.append(list(messages))
        step = self.script.pop(0)
        if isinstance(step, str):
            return ModelResponse(Message.assistant(step), Usage(10, 5), "end")
        calls = [ToolCall(id=f"c{i}", name=n, arguments=a) for i, (n, a) in enumerate(step)]
        return ModelResponse(Message.assistant("", calls), Usage(10, 5), "tool_use")
