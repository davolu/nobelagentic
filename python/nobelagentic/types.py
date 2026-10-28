"""Provider-neutral message, tool-call and event types.

Every provider adapter translates to and from these. Nothing above the
provider layer ever sees a vendor-specific object.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    # For role == "tool": which call this message answers
    tool_call_id: str | None = None
    name: str | None = None

    # Convenience constructors -------------------------------------------
    @staticmethod
    def system(text: str) -> "Message":
        return Message("system", text)

    @staticmethod
    def user(text: str) -> "Message":
        return Message("user", text)

    @staticmethod
    def assistant(text: str = "", tool_calls: list[ToolCall] | None = None) -> "Message":
        return Message("assistant", text, tool_calls or [])

    @staticmethod
    def tool(call_id: str, name: str, result: str) -> "Message":
        return Message("tool", result, tool_call_id=call_id, name=name)


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens)


@dataclass
class ModelResponse:
    message: Message
    usage: Usage = field(default_factory=Usage)
    stop_reason: str = "end"  # "end" | "tool_use" | "max_tokens"
    raw: Any = None


# Stream events ----------------------------------------------------------
# Every run emits a stream of these. `agent.stream()` yields them; `agent.run()`
# consumes them and returns the final RunResult.

@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCallStart:
    call: ToolCall


@dataclass
class ToolCallEnd:
    call: ToolCall
    result: str
    error: bool = False


@dataclass
class StepEnd:
    step: int
    usage: Usage


@dataclass
class Handoff:
    from_agent: str
    to_agent: str
    reason: str


@dataclass
class RunEnd:
    output: str
    usage: Usage
    steps: int


Event = TextDelta | ToolCallStart | ToolCallEnd | StepEnd | Handoff | RunEnd


@dataclass
class RunResult:
    output: str
    messages: list[Message]
    usage: Usage
    steps: int
    agent: str

    def __str__(self) -> str:  # so print(agent.run(...)) just works
        return self.output
