import { z } from "zod";
import { tool } from "../tools.js";

export const webSearch = tool({
  name: "web_search",
  description: "Search the web (DuckDuckGo HTML). Returns title, url, snippet per result.",
  parameters: z.object({ query: z.string(), max_results: z.number().int().min(1).max(20).default(5) }),
  execute: async ({ query, max_results }) => {
    const r = await fetch(`https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`, { headers: { "User-Agent": "nobelagentic/0.1" } });
    const html = await r.text();
    const out: { title: string; url: string; snippet: string }[] = [];
    const re = /<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)<\/a>[\s\S]*?<a[^>]+class="result__snippet"[^>]*>(.*?)<\/a>/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(html)) && out.length < max_results) {
      const strip = (s: string) => s.replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&quot;/g, '"').trim();
      out.push({ title: strip(m[2]), url: m[1], snippet: strip(m[3]) });
    }
    return out;
  },
});

export const fetchUrl = tool({
  name: "fetch_url",
  description: "Fetch a web page and return its visible text (HTML stripped).",
  parameters: z.object({ url: z.string().url(), max_chars: z.number().int().default(8000) }),
  execute: async ({ url, max_chars }) => {
    const r = await fetch(url, { headers: { "User-Agent": "nobelagentic/0.1" } });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    let text = await r.text();
    if ((r.headers.get("content-type") ?? "").includes("html"))
      text = text.replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, " ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
    return text.slice(0, max_chars);
  },
});

export const httpRequest = tool({
  name: "http_request",
  description: "Make an HTTP request and return status, headers and body text.",
  parameters: z.object({ method: z.string(), url: z.string().url(), body: z.string().optional(), headers: z.record(z.string()).optional() }),
  execute: async ({ method, url, body, headers }) => {
    const r = await fetch(url, { method: method.toUpperCase(), body, headers });
    return { status: r.status, headers: Object.fromEntries([...(r.headers as any)]), body: (await r.text()).slice(0, 8000) };
  },
});

export const TOOLS = [webSearch, fetchUrl, httpRequest];
