"""Anthropic Messages API adapter."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from ..types import Message, ModelResponse, TextDelta, Usage
from .base import Provider, ProviderError, tool_call_from_json


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, model: str, **kwargs: Any):
        super().__init__(model, **kwargs)
        try:
            import anthropic
        except ImportError as e:
            raise ProviderError("pip install anthropic  (or nobelagentic[anthropic])") from e
        self.client = anthropic.AsyncAnthropic(**{k: v for k, v in kwargs.items() if k in {"api_key", "base_url"}})

    # ---- translation -------------------------------------------------
    @staticmethod
    def _to_api(messages: list[Message]) -> tuple[str | None, list[dict]]:
        system = None
        out: list[dict] = []
        for m in messages:
            if m.role == "system":
                system = (system + "\n\n" + m.content) if system else m.content
            elif m.role == "user":
                out.append({"role": "user", "content": m.content})
            elif m.role == "assistant":
                blocks: list[dict] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
            elif m.role == "tool":
                block = {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
                # Anthropic wants consecutive tool results merged into one user turn
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list) \
                        and out[-1]["content"] and out[-1]["content"][0].get("type") == "tool_result":
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
        return system, out

    @staticmethod
    def _tools(tools: list[dict]) -> list[dict]:
        return [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]

    # ---- calls ---------------------------------------------------------
    async def complete(self, messages, tools, max_tokens=4096) -> ModelResponse:
        system, api_msgs = self._to_api(messages)
        req: dict[str, Any] = dict(model=self.model, messages=api_msgs, max_tokens=max_tokens)
        if system:
            req["system"] = system
        if tools:
            req["tools"] = self._tools(tools)
        resp = await self.client.messages.create(**req)
        text, calls = "", []
        for block in resp.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                calls.append(tool_call_from_json(block.id, block.name, block.input))
        return ModelResponse(
            message=Message.assistant(text, calls),
            usage=Usage(resp.usage.input_tokens, resp.usage.output_tokens),
            stop_reason="tool_use" if calls else "end",
            raw=resp,
        )

    async def stream(self, messages, tools, max_tokens=4096) -> AsyncIterator[TextDelta | ModelResponse]:
        system, api_msgs = self._to_api(messages)
        req: dict[str, Any] = dict(model=self.model, messages=api_msgs, max_tokens=max_tokens)
        if system:
            req["system"] = system
        if tools:
            req["tools"] = self._tools(tools)
        text, calls = "", []
        current_tool: dict | None = None
        usage = Usage()
        async with self.client.messages.stream(**req) as s:
            async for ev in s:
                t = ev.type
                if t == "content_block_start" and ev.content_block.type == "tool_use":
                    current_tool = {"id": ev.content_block.id, "name": ev.content_block.name, "json": ""}
                elif t == "content_block_delta":
                    d = ev.delta
                    if d.type == "text_delta":
                        text += d.text
                        yield TextDelta(d.text)
                    elif d.type == "input_json_delta" and current_tool is not None:
                        current_tool["json"] += d.partial_json
                elif t == "content_block_stop" and current_tool is not None:
                    calls.append(tool_call_from_json(current_tool["id"], current_tool["name"], current_tool["json"]))
                    current_tool = None
                elif t == "message_start":
                    usage.input_tokens = ev.message.usage.input_tokens
                elif t == "message_delta":
                    usage.output_tokens = ev.usage.output_tokens
        yield ModelResponse(Message.assistant(text, calls), usage, "tool_use" if calls else "end")
