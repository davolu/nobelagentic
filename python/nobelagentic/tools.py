"""Tools: plain functions become schemas automatically.

    @tool
    def get_weather(city: str, units: str = "c") -> str:
        \"\"\"Current weather for a city.\"\"\"
        ...

No schema writing. Type hints + docstring are the schema. Sync and async both work.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import types
import typing
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Union, get_args, get_origin

from pydantic import TypeAdapter, ValidationError

_JSON_TYPES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _annotation_to_schema(ann: Any) -> dict[str, Any]:
    """Best-effort JSON schema from a Python annotation. Falls back to pydantic."""
    if ann is inspect.Parameter.empty or ann is Any:
        return {}
    origin = get_origin(ann)
    if origin is Union or isinstance(ann, types.UnionType):  # Optional[X] / X | None
        inner = [a for a in get_args(ann) if a is not type(None)]
        if len(inner) == 1:
            return _annotation_to_schema(inner[0])
    if origin is list:
        (item,) = get_args(ann) or (Any,)
        return {"type": "array", "items": _annotation_to_schema(item)}
    if origin is typing.Literal:
        return {"type": "string", "enum": list(get_args(ann))}
    if ann in _JSON_TYPES:
        return {"type": _JSON_TYPES[ann]}
    try:
        return TypeAdapter(ann).json_schema()
    except Exception:
        return {"type": "string"}


def _parse_docstring(doc: str | None) -> tuple[str, dict[str, str]]:
    """Returns (summary, {param: description}). Supports 'Args:' / 'name: desc' blocks."""
    if not doc:
        return "", {}
    lines = [l.strip() for l in doc.strip().splitlines()]
    summary_lines: list[str] = []
    params: dict[str, str] = {}
    in_args = False
    for line in lines:
        if line.lower().rstrip(":") in {"args", "arguments", "params", "parameters"}:
            in_args = True
            continue
        if in_args and ":" in line:
            name, _, desc = line.partition(":")
            params[name.strip().split(" ")[0]] = desc.strip()
        elif not in_args and line:
            summary_lines.append(line)
    return " ".join(summary_lines), params


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema
    fn: Callable[..., Any] | Callable[..., Awaitable[Any]]
    pack: str | None = None
    requires: list[str] = field(default_factory=list)  # env vars needed

    async def call(self, arguments: dict[str, Any]) -> str:
        try:
            result = self.fn(**arguments)
            if inspect.isawaitable(result):
                result = await result
        except TypeError as e:
            raise ToolError(f"Bad arguments for {self.name}: {e}") from e
        return _stringify(result)

    def to_schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


class ToolError(Exception):
    pass


def _stringify(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception:
        return str(result)


def tool(fn: Callable | None = None, *, name: str | None = None, description: str | None = None,
         pack: str | None = None, requires: list[str] | None = None):
    """Decorator: turn a function into a Tool. Works bare or with options."""

    def wrap(f: Callable) -> Tool:
        sig = inspect.signature(f)
        hints = typing.get_type_hints(f) if hasattr(f, "__annotations__") else {}
        summary, param_docs = _parse_docstring(f.__doc__)
        props: dict[str, Any] = {}
        required: list[str] = []
        for pname, p in sig.parameters.items():
            if pname in {"self", "cls"} or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                continue
            schema = _annotation_to_schema(hints.get(pname, p.annotation))
            if pname in param_docs:
                schema = {**schema, "description": param_docs[pname]}
            if p.default is inspect.Parameter.empty:
                required.append(pname)
            else:
                schema = {**schema, "default": p.default}
            props[pname] = schema
        t = Tool(
            name=name or f.__name__,
            description=description or summary or f.__name__.replace("_", " "),
            parameters={"type": "object", "properties": props, "required": required},
            fn=f,
            pack=pack,
            requires=requires or [],
        )
        return t

    return wrap(fn) if fn is not None else wrap


def coerce_tool(obj: Any) -> Tool:
    """Accept a Tool, a @tool-decorated function or a bare function."""
    if isinstance(obj, Tool):
        return obj
    if callable(obj):
        return tool(obj)
    raise TypeError(f"Not a tool: {obj!r}")
