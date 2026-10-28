"""Agent: the one-liner API.

    agent = Agent("You help plan trips", tools=[get_weather, "web"])
    agent.run("Plan a trip to Lagos")              # sync → RunResult
    await agent.arun("...")                        # async
    async for event in agent.stream("..."): ...    # events

Under the hood it's a ReAct loop: model → tool calls → results → model → ... → final answer.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, AsyncIterator, Callable, Iterable

from .providers import Provider, resolve
from .tools import Tool, ToolError, coerce_tool, tool
from .types import (Event, Handoff, Message, ModelResponse, RunEnd, RunResult, StepEnd,
                    TextDelta, ToolCallEnd, ToolCallStart, Usage)


class Agent:
    def __init__(
        self,
        instructions: str = "You are a helpful assistant.",
        *,
        name: str = "agent",
        model: str | Provider | None = None,
        tools: Iterable[Any] = (),
        mcp: Iterable[Any] = (),
        handoffs: Iterable["Agent"] = (),
        max_steps: int = 25,
        max_tokens: int = 4096,
        parallel_tools: bool = True,
        on_event: Callable[[Event], None] | None = None,
    ):
        self.name = name
        self.instructions = instructions
        self._model = model
        self._provider: Provider | None = None
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.parallel_tools = parallel_tools
        self.on_event = on_event
        self.handoffs: dict[str, Agent] = {a.name: a for a in handoffs}
        self._mcp_specs = list(mcp)
        self._mcp_loaded = False
        self.tools: dict[str, Tool] = {}
        for t in tools:
            self.add_tool(t)
        for target in self.handoffs.values():
            self.add_tool(self._handoff_tool(target))

    # ---- setup ----------------------------------------------------------
    @property
    def provider(self) -> Provider:
        if self._provider is None:
            self._provider = resolve(self._model)
        return self._provider

    def add_tool(self, obj: Any) -> None:
        """Accepts a Tool, a function, or a pack name like "web" / "files"."""
        if isinstance(obj, str):
            from .packs import load_pack
            for t in load_pack(obj):
                self.tools[t.name] = t
            return
        t = coerce_tool(obj)
        missing = [v for v in t.requires if not os.environ.get(v)]
        if missing:
            raise ToolError(f"Tool '{t.name}' needs env var(s): {', '.join(missing)}")
        self.tools[t.name] = t

    def _handoff_tool(self, target: "Agent") -> Tool:
        def _fn(reason: str = "") -> str:
            return f"__handoff__:{target.name}:{reason}"
        return tool(
            _fn,
            name=f"handoff_to_{target.name}",
            description=f"Hand the conversation to the '{target.name}' agent. {target.instructions[:120]}",
        )

    async def _load_mcp(self) -> None:
        if self._mcp_loaded or not self._mcp_specs:
            return
        from .mcp import connect
        for spec in self._mcp_specs:
            for t in await connect(spec):
                self.tools[t.name] = t
        self._mcp_loaded = True

    # ---- public API -------------------------------------------------------
    def run(self, input: str | list[Message], **kw: Any) -> RunResult:
        return asyncio.run(self.arun(input, **kw))

    async def arun(self, input: str | list[Message], **kw: Any) -> RunResult:
        result: RunResult | None = None
        async for ev in self.stream(input, **kw):
            if isinstance(ev, RunEnd):
                result = self._last_result
        assert result is not None
        return result

    async def stream(self, input: str | list[Message], *, history: list[Message] | None = None) -> AsyncIterator[Event]:
        await self._load_mcp()
        messages: list[Message] = [Message.system(self.instructions)]
        if history:
            messages += history
        messages += [Message.user(input)] if isinstance(input, str) else input

        total = Usage()
        steps = 0
        agent: Agent = self

        while steps < agent.max_steps:
            steps += 1
            schemas = [t.to_schema() for t in agent.tools.values()]
            response: ModelResponse | None = None
            async for chunk in agent.provider.stream(messages, schemas, agent.max_tokens):
                if isinstance(chunk, TextDelta):
                    yield self._emit(chunk)
                else:
                    response = chunk
            assert response is not None
            total = total + response.usage
            messages.append(response.message)
            yield self._emit(StepEnd(steps, response.usage))

            if not response.message.tool_calls:
                break

            # Execute tools (parallel by default)
            calls = response.message.tool_calls
            for c in calls:
                yield self._emit(ToolCallStart(c))
            if agent.parallel_tools:
                results = await asyncio.gather(*(agent._exec(c) for c in calls))
            else:
                results = [await agent._exec(c) for c in calls]

            handoff_to: Agent | None = None
            for call, (text, is_err) in zip(calls, results):
                yield self._emit(ToolCallEnd(call, text, is_err))
                messages.append(Message.tool(call.id, call.name, text))
                if text.startswith("__handoff__:"):
                    _, target, reason = text.split(":", 2)
                    handoff_to = agent.handoffs[target]
                    yield self._emit(Handoff(agent.name, target, reason))
            if handoff_to is not None:
                agent = handoff_to
                messages[0] = Message.system(agent.instructions)

        output = next((m.content for m in reversed(messages) if m.role == "assistant" and m.content), "")
        self._last_result = RunResult(output, messages, total, steps, agent.name)
        yield self._emit(RunEnd(output, total, steps))

    # ---- internals -----------------------------------------------------------
    async def _exec(self, call) -> tuple[str, bool]:
        t = self.tools.get(call.name)
        if t is None:
            return f"Error: unknown tool '{call.name}'. Available: {', '.join(self.tools)}", True
        try:
            return await t.call(call.arguments), False
        except Exception as e:  # tool errors go back to the model, never crash the run
            return f"Error from {call.name}: {type(e).__name__}: {e}", True

    def _emit(self, ev: Event) -> Event:
        if self.on_event:
            self.on_event(ev)
        return ev

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, tools={list(self.tools)})"
