"""files pack: read, write, list, search. Sandboxed to a root directory."""
from __future__ import annotations

import os
import re
from pathlib import Path

from ..tools import tool

ROOT = Path(os.environ.get("AGENTX_FILES_ROOT", ".")).resolve()


def _safe(path: str) -> Path:
    p = (ROOT / path).resolve()
    if ROOT not in p.parents and p != ROOT:
        raise PermissionError(f"Path escapes allowed root {ROOT}")
    return p


@tool
def read_file(path: str, max_chars: int = 20000) -> str:
    """Read a text file. Relative to the agent's working directory."""
    return _safe(path).read_text(errors="replace")[:max_chars]


@tool
def write_file(path: str, content: str) -> str:
    """Write (or overwrite) a text file. Creates parent folders."""
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content)} chars to {path}"


@tool
def append_file(path: str, content: str) -> str:
    """Append text to a file."""
    with _safe(path).open("a") as f:
        f.write(content)
    return f"appended {len(content)} chars to {path}"


@tool
def list_dir(path: str = ".", recursive: bool = False) -> list[str]:
    """List files in a directory."""
    p = _safe(path)
    it = p.rglob("*") if recursive else p.iterdir()
    return sorted(str(x.relative_to(ROOT)) for x in it if ".git" not in x.parts)[:500]


@tool
def search_files(pattern: str, path: str = ".", glob: str = "*") -> list[dict]:
    """Regex search inside files. Returns file, line number and matching line."""
    rx = re.compile(pattern)
    hits = []
    for f in _safe(path).rglob(glob):
        if not f.is_file() or ".git" in f.parts:
            continue
        try:
            for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if rx.search(line):
                    hits.append({"file": str(f.relative_to(ROOT)), "line": i, "text": line.strip()[:200]})
                    if len(hits) >= 200:
                        return hits
        except OSError:
            continue
    return hits


@tool
def delete_file(path: str) -> str:
    """Delete a file."""
    _safe(path).unlink()
    return f"deleted {path}"


TOOLS = [read_file, write_file, append_file, list_dir, search_files, delete_file]
