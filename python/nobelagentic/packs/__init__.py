"""Built-in tool packs. Lazy-loaded by name: Agent(tools=["web", "files"]).

Each pack is a module exposing a `TOOLS` list. Add a pack by dropping a file here
and listing it in PACKS.
"""
from __future__ import annotations

import importlib

from ..tools import Tool

PACKS: dict[str, str] = {
    "web": "nobelagentic.packs.web",
    "files": "nobelagentic.packs.files",
    "shell": "nobelagentic.packs.shell",
    "time": "nobelagentic.packs.time_",
    "math": "nobelagentic.packs.math_",
    "data": "nobelagentic.packs.data",
}


def load_pack(name: str) -> list[Tool]:
    if name not in PACKS:
        raise KeyError(f"Unknown tool pack '{name}'. Available: {', '.join(PACKS)}")
    mod = importlib.import_module(PACKS[name])
    tools: list[Tool] = list(mod.TOOLS)
    for t in tools:
        t.pack = name
    return tools


def all_tools() -> dict[str, list[Tool]]:
    return {name: load_pack(name) for name in PACKS}
