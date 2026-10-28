import pytest

from nobelagentic import Agent, Handoff, RunEnd, TextDelta, ToolCallEnd, ToolCallStart, tool
from nobelagentic.tools import Tool

from .fake_provider import FakeProvider


@tool
def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: first
        b: second
    """
    return a + b


def test_tool_schema_from_signature():
    assert isinstance(add, Tool)
    s = add.to_schema()
    assert s["name"] == "add"
    assert s["description"] == "Add two numbers."
    assert s["parameters"]["properties"]["a"] == {"type": "integer", "description": "first"}
    assert s["parameters"]["required"] == ["a", "b"]


def test_optional_and_list_params():
    @tool
    def f(names: list[str], limit: int = 3, tag: str | None = None) -> str:
        return ""
    p = f.parameters["properties"]
    assert p["names"] == {"type": "array", "items": {"type": "string"}}
    assert p["limit"]["default"] == 3
    assert p["tag"]["type"] == "string"
    assert f.parameters["required"] == ["names"]


def test_react_loop_calls_tool_and_returns_answer():
    provider = FakeProvider([[("add", {"a": 2, "b": 3})], "The answer is 5."])
    agent = Agent("calc", model=provider, tools=[add])
    result = agent.run("2+3?")
    assert result.output == "The answer is 5."
    assert result.steps == 2
    assert result.usage.input_tokens == 20
    # tool result was fed back
    tool_msgs = [m for m in result.messages if m.role == "tool"]
    assert tool_msgs[0].content == "5"


def test_unknown_tool_error_is_returned_to_model_not_raised():
    provider = FakeProvider([[("nope", {})], "ok"])
    result = Agent("x", model=provider, tools=[add]).run("hi")
    assert "unknown tool" in [m for m in result.messages if m.role == "tool"][0].content
    assert result.output == "ok"


def test_tool_exception_is_captured():
    @tool
    def boom() -> str:
        """Explode."""
        raise RuntimeError("kaboom")
    provider = FakeProvider([[("boom", {})], "recovered"])
    result = Agent("x", model=provider, tools=[boom]).run("go")
    assert "kaboom" in [m for m in result.messages if m.role == "tool"][0].content


@pytest.mark.asyncio
async def test_stream_events_order():
    provider = FakeProvider([[("add", {"a": 1, "b": 1})], "2"])
    events = [ev async for ev in Agent("x", model=provider, tools=[add]).stream("1+1")]
    kinds = [type(e).__name__ for e in events]
    assert kinds == ["StepEnd", "ToolCallStart", "ToolCallEnd", "TextDelta", "StepEnd", "RunEnd"]
    assert isinstance(events[-1], RunEnd)
    assert any(isinstance(e, TextDelta) and e.text == "2" for e in events)


def test_packs_load_by_name():
    agent = Agent("x", model=FakeProvider(["hi"]), tools=["math", "time"])
    assert "calculate" in agent.tools and "now" in agent.tools


def test_parallel_tool_calls():
    provider = FakeProvider([[("add", {"a": 1, "b": 1}), ("add", {"a": 2, "b": 2})], "done"])
    result = Agent("x", model=provider, tools=[add]).run("go")
    assert [m.content for m in result.messages if m.role == "tool"] == ["2", "4"]


def test_handoff_switches_agent():
    target = Agent("I am B", name="b", model=FakeProvider(["hello from b"]))
    triage = Agent("route", name="a", model=FakeProvider([[("handoff_to_b", {"reason": "lang"})]]), handoffs=[target])
    events = []
    result = None
    import asyncio

    async def go():
        nonlocal result
        async for ev in triage.stream("hi"):
            events.append(ev)
        return triage._last_result
    result = asyncio.run(go())
    assert any(isinstance(e, Handoff) and e.to_agent == "b" for e in events)
    assert result.output == "hello from b"
    assert result.agent == "b"


def test_max_steps_stops_runaway():
    provider = FakeProvider([[("add", {"a": 1, "b": 1})]] * 5 + ["never"])
    result = Agent("x", model=provider, tools=[add], max_steps=3).run("loop")
    assert result.steps == 3
