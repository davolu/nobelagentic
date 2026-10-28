"""OpenAI-compatible adapter: OpenAI, Gemini (OpenAI endpoint), Ollama, Groq, OpenRouter, Together.

One adapter covers all of them because they all speak the chat.completions dialect.
"""
from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

from ..types import Message, ModelResponse, TextDelta, Usage
from .base import Provider, ProviderError, tool_call_from_json

_VENDORS = {
    "openai": ("OPENAI_API_KEY", None),
    "gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    "ollama": (None, "http://localhost:11434/v1"),
    "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1"),
    "openrouter": ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
    "together": ("TOGETHER_API_KEY", "https://api.together.xyz/v1"),
}


class OpenAICompatProvider(Provider):
    name = "openai"

    def __init__(self, model: str, vendor: str = "openai", **kwargs: Any):
        super().__init__(model, **kwargs)
        try:
            import openai
        except ImportError as e:
            raise ProviderError("pip install openai  (or swarmagents[openai])") from e
        env_var, base_url = _VENDORS[vendor]
        api_key = kwargs.get("api_key") or (os.environ.get(env_var) if env_var else "ollama")
        if not api_key:
            raise ProviderError(f"{vendor}: set {env_var} or pass api_key=")
        self.name = vendor
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=kwargs.get("base_url") or base_url)

    @staticmethod
    def _to_api(messages: list[Message]) -> list[dict]:
        out = []
        for m in messages:
            if m.role == "assistant":
                d: dict[str, Any] = {"role": "assistant", "content": m.content or None}
                if m.tool_calls:
                    d["tool_calls"] = [{
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    } for tc in m.tool_calls]
                out.append(d)
            elif m.role == "tool":
                out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    @staticmethod
    def _tools(tools: list[dict]) -> list[dict]:
        return [{"type": "function", "function": {
            "name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in tools]

    async def complete(self, messages, tools, max_tokens=4096) -> ModelResponse:
        req: dict[str, Any] = dict(model=self.model, messages=self._to_api(messages), max_tokens=max_tokens)
        if tools:
            req["tools"] = self._tools(tools)
        resp = await self.client.chat.completions.create(**req)
        choice = resp.choices[0]
        calls = [tool_call_from_json(tc.id, tc.function.name, tc.function.arguments)
                 for tc in (choice.message.tool_calls or [])]
        usage = Usage(resp.usage.prompt_tokens, resp.usage.completion_tokens) if resp.usage else Usage()
        return ModelResponse(Message.assistant(choice.message.content or "", calls), usage,
                             "tool_use" if calls else "end", raw=resp)

    async def stream(self, messages, tools, max_tokens=4096) -> AsyncIterator[TextDelta | ModelResponse]:
        req: dict[str, Any] = dict(model=self.model, messages=self._to_api(messages), max_tokens=max_tokens,
                                   stream=True, stream_options={"include_usage": True})
        if tools:
            req["tools"] = self._tools(tools)
        text = ""
        partial: dict[int, dict] = {}
        usage = Usage()
        async for chunk in await self.client.chat.completions.create(**req):
            if chunk.usage:
                usage = Usage(chunk.usage.prompt_tokens, chunk.usage.completion_tokens)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                text += delta.content
                yield TextDelta(delta.content)
            for tc in delta.tool_calls or []:
                slot = partial.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    slot["args"] += tc.function.arguments
        calls = [tool_call_from_json(p["id"], p["name"], p["args"]) for _, p in sorted(partial.items())]
        yield ModelResponse(Message.assistant(text, calls), usage, "tool_use" if calls else "end")
