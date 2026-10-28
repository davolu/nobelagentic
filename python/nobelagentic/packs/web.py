"""web pack: search + fetch. No API key needed."""
from __future__ import annotations

import re

import httpx

from ..tools import tool


@tool
async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web (DuckDuckGo). Returns title, url, snippet per result.

    Args:
        query: What to search for.
        max_results: How many results to return (1-20).
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return [{"error": "pip install duckduckgo-search"}]
    with DDGS() as ddgs:
        return [{"title": r["title"], "url": r["href"], "snippet": r["body"]}
                for r in ddgs.text(query, max_results=max(1, min(max_results, 20)))]


@tool
async def fetch_url(url: str, max_chars: int = 8000) -> str:
    """Fetch a web page and return its visible text (HTML stripped).

    Args:
        url: Full http(s) URL.
        max_chars: Truncate the text to this many characters.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=20, headers={"User-Agent": "nobelagentic/0.1"}) as c:
        r = await c.get(url)
        r.raise_for_status()
    text = r.text
    if "html" in r.headers.get("content-type", ""):
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


@tool
async def http_request(method: str, url: str, body: str | None = None, headers: dict | None = None) -> dict:
    """Make an HTTP request and return status, headers and body text."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
        r = await c.request(method.upper(), url, content=body, headers=headers)
    return {"status": r.status_code, "headers": dict(r.headers), "body": r.text[:8000]}


TOOLS = [web_search, fetch_url, http_request]
