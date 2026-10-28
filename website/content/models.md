---
title: Models
nav: Models
order: 3
---
# Models

Every provider sits behind one interface. Your agent code never sees a vendor SDK object.

## Picking a model

```python
Agent("...")                              # auto: first provider with a key in env
Agent("...", model="claude-opus-5-5")     # prefix → Anthropic
Agent("...", model="gpt-5")               # prefix → OpenAI
Agent("...", model="openai:gpt-5")        # explicit
Agent("...", model="ollama:llama3.1")     # local
Agent("...", model="groq:llama-3.3-70b")  # any OpenAI-compatible host
```

Auto-detection order: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`.

## Supported providers

| Provider | Env var | Notes |
|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | Native adapter, real streaming |
| OpenAI | `OPENAI_API_KEY` | |
| Gemini | `GEMINI_API_KEY` | Via Google's OpenAI-compatible endpoint |
| Ollama | — | `http://localhost:11434` |
| Groq | `GROQ_API_KEY` | |
| OpenRouter | `OPENROUTER_API_KEY` | |
| Together | `TOGETHER_API_KEY` | |

## Bring your own

Subclass `Provider` and implement `complete()`. Streaming is optional; the default fakes deltas from a full response.

```python
from swarmagents import Provider, Message, Usage
from swarmagents.types import ModelResponse

class MyProvider(Provider):
    async def complete(self, messages, tools, max_tokens=4096) -> ModelResponse:
        ...
        return ModelResponse(Message.assistant(text, calls), Usage(i, o))

Agent("...", model=MyProvider("my-model"))
```

This is also how the test suite runs offline: a `FakeProvider` replays a script of responses.
