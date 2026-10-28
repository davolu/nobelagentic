"""The one Provider interface every model speaks through."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from ..types import Message, ModelResponse, TextDelta, ToolCall


class Provider(ABC):
    name: str = "base"

    def __init__(self, model: str, **kwargs: Any):
        self.model = model
        self.kwargs = kwargs

    @abstractmethod
    async def complete(self, messages: list[Message], tools: list[dict[str, Any]],
                       max_tokens: int = 4096) -> ModelResponse: ...

    async def stream(self, messages: list[Message], tools: list[dict[str, Any]],
                     max_tokens: int = 4096) -> AsyncIterator[TextDelta | ModelResponse]:
        """Default streaming = fake it from complete(). Adapters override for real deltas."""
        resp = await self.complete(messages, tools, max_tokens)
        if resp.message.content:
            yield TextDelta(resp.message.content)
        yield resp


class ProviderError(Exception):
    pass


def _env(name: str) -> str | None:
    v = os.environ.get(name)
    return v if v else None


# model-name prefix → provider. Users can also pass "provider:model".
_PREFIXES = {
    "claude": "anthropic",
    "gpt": "openai",
    "o1": "openai", "o3": "openai", "o4": "openai",
    "gemini": "gemini",
    "llama": "ollama", "mistral": "ollama", "qwen": "ollama", "phi": "ollama",
}

_DEFAULTS = {  # provider → (env var, default model)
    "anthropic": ("ANTHROPIC_API_KEY", "claude-sonnet-5-5"),
    "openai": ("OPENAI_API_KEY", "gpt-5"),
    "gemini": ("GEMINI_API_KEY", "gemini-2.5-pro"),
    "ollama": (None, "llama3.1"),
}


def resolve(model: str | Provider | None = None, **kwargs: Any) -> Provider:
    """Turn a model string (or nothing) into a Provider.

    resolve()                     → first provider with an API key in env
    resolve("claude-opus-5-5")    → anthropic
    resolve("openai:gpt-5")       → explicit
    resolve(MyProvider(...))      → passthrough
    """
    if isinstance(model, Provider):
        return model

    provider_name: str | None = None
    model_name: str | None = model

    if model and ":" in model and not model.startswith("http"):
        provider_name, model_name = model.split(":", 1)
    elif model:
        for prefix, prov in _PREFIXES.items():
            if model.lower().startswith(prefix):
                provider_name = prov
                break
        if provider_name is None:
            provider_name = "openai"  # most OpenAI-compatible servers accept anything
    else:
        for prov, (env_var, default_model) in _DEFAULTS.items():
            if env_var and _env(env_var):
                provider_name, model_name = prov, default_model
                break
        if provider_name is None:
            raise ProviderError(
                "No model configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY or GEMINI_API_KEY, "
                "or pass model='ollama:llama3.1' for a local model."
            )

    model_name = model_name or _DEFAULTS[provider_name][1]
    return _build(provider_name, model_name, **kwargs)


def _build(provider_name: str, model: str, **kwargs: Any) -> Provider:
    if provider_name == "anthropic":
        from .anthropic import AnthropicProvider
        return AnthropicProvider(model, **kwargs)
    if provider_name in {"openai", "gemini", "ollama", "groq", "openrouter", "together"}:
        from .openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(model, vendor=provider_name, **kwargs)
    raise ProviderError(f"Unknown provider '{provider_name}'. Known: anthropic, openai, gemini, ollama, groq, openrouter, together")


def tool_call_from_json(id: str, name: str, args: str | dict) -> ToolCall:
    import json
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except json.JSONDecodeError:
            args = {"_raw": args}
    return ToolCall(id=id, name=name, arguments=args)
