"""data pack: JSON / CSV helpers."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from ..tools import tool


@tool
def parse_json(text: str) -> Any:
    """Parse a JSON string and return the structured value."""
    return json.loads(text)


@tool
def json_query(data: str, path: str) -> Any:
    """Extract a value from JSON using dotted path, e.g. 'items.0.name'."""
    cur: Any = json.loads(data)
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


@tool
def csv_to_json(text: str) -> list[dict]:
    """Convert CSV text (with header row) to a list of objects."""
    return list(csv.DictReader(io.StringIO(text)))


@tool
def json_to_csv(rows: list[dict]) -> str:
    """Convert a list of objects to CSV text."""
    if not rows:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


@tool
def summarize_table(rows: list[dict]) -> dict:
    """Basic stats for numeric columns: count, min, max, mean."""
    out: dict[str, dict] = {}
    for key in rows[0] if rows else []:
        nums = []
        for r in rows:
            try:
                nums.append(float(r[key]))
            except (TypeError, ValueError, KeyError):
                pass
        if nums:
            out[key] = {"count": len(nums), "min": min(nums), "max": max(nums), "mean": sum(nums) / len(nums)}
    return out


TOOLS = [parse_json, json_query, csv_to_json, json_to_csv, summarize_table]
