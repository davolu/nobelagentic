import { z } from "zod";
import { tool } from "../tools.js";

export const parseJson = tool({ name: "parse_json", description: "Parse a JSON string.", parameters: z.object({ text: z.string() }), execute: ({ text }) => JSON.parse(text) });
export const jsonQuery = tool({ name: "json_query", description: "Extract a value from JSON using a dotted path, e.g. 'items.0.name'.",
  parameters: z.object({ data: z.string(), path: z.string() }),
  execute: ({ data, path }) => path.split(".").reduce((cur: any, k) => cur[k], JSON.parse(data)) });
export const csvToJson = tool({ name: "csv_to_json", description: "Convert CSV text (with header row) to a list of objects.",
  parameters: z.object({ text: z.string() }),
  execute: ({ text }) => { const [h, ...rows] = text.trim().split("\n").map((l) => l.split(",")); return rows.map((r) => Object.fromEntries(h.map((k, i) => [k.trim(), r[i]?.trim()]))); } });
export const jsonToCsv = tool({ name: "json_to_csv", description: "Convert a list of objects to CSV text.",
  parameters: z.object({ rows: z.array(z.record(z.any())) }),
  execute: ({ rows }) => { if (!rows.length) return ""; const keys = Object.keys(rows[0]); return [keys.join(","), ...rows.map((r) => keys.map((k) => String(r[k] ?? "")).join(","))].join("\n"); } });
export const summarizeTable = tool({ name: "summarize_table", description: "Basic stats for numeric columns: count, min, max, mean.",
  parameters: z.object({ rows: z.array(z.record(z.any())) }),
  execute: ({ rows }) => { const out: Record<string, any> = {}; for (const k of Object.keys(rows[0] ?? {})) { const n = rows.map((r) => Number(r[k])).filter((x) => !isNaN(x)); if (n.length) out[k] = { count: n.length, min: Math.min(...n), max: Math.max(...n), mean: n.reduce((a, b) => a + b, 0) / n.length }; } return out; } });
export const TOOLS = [parseJson, jsonQuery, csvToJson, jsonToCsv, summarizeTable];
