import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import { tool } from "../tools.js";

const ROOT = path.resolve(process.env.SWARMAGENTS_FILES_ROOT ?? ".");
const safe = (p: string) => {
  const abs = path.resolve(ROOT, p);
  if (abs !== ROOT && !abs.startsWith(ROOT + path.sep)) throw new Error(`Path escapes allowed root ${ROOT}`);
  return abs;
};
async function walk(dir: string, recursive: boolean): Promise<string[]> {
  const out: string[] = [];
  for (const e of await fs.readdir(dir, { withFileTypes: true })) {
    if (e.name === ".git" || e.name === "node_modules") continue;
    const full = path.join(dir, e.name);
    out.push(path.relative(ROOT, full));
    if (recursive && e.isDirectory()) out.push(...(await walk(full, true)));
  }
  return out;
}

export const readFile = tool({ name: "read_file", description: "Read a text file.",
  parameters: z.object({ path: z.string(), max_chars: z.number().int().default(20000) }),
  execute: async ({ path: p, max_chars }) => (await fs.readFile(safe(p), "utf8")).slice(0, max_chars) });
export const writeFile = tool({ name: "write_file", description: "Write (or overwrite) a text file. Creates parent folders.",
  parameters: z.object({ path: z.string(), content: z.string() }),
  execute: async ({ path: p, content }) => { const f = safe(p); await fs.mkdir(path.dirname(f), { recursive: true }); await fs.writeFile(f, content); return `wrote ${content.length} chars to ${p}`; } });
export const appendFile = tool({ name: "append_file", description: "Append text to a file.",
  parameters: z.object({ path: z.string(), content: z.string() }),
  execute: async ({ path: p, content }) => { await fs.appendFile(safe(p), content); return `appended ${content.length} chars to ${p}`; } });
export const listDir = tool({ name: "list_dir", description: "List files in a directory.",
  parameters: z.object({ path: z.string().default("."), recursive: z.boolean().default(false) }),
  execute: async ({ path: p, recursive }) => (await walk(safe(p), recursive)).sort().slice(0, 500) });
export const searchFiles = tool({ name: "search_files", description: "Regex search inside files. Returns file, line and text.",
  parameters: z.object({ pattern: z.string(), path: z.string().default(".") }),
  execute: async ({ pattern, path: p }) => {
    const rx = new RegExp(pattern); const hits: { file: string; line: number; text: string }[] = [];
    for (const rel of await walk(safe(p), true)) {
      const abs = path.join(ROOT, rel);
      if (!(await fs.stat(abs)).isFile()) continue;
      const lines = (await fs.readFile(abs, "utf8").catch(() => "")).split("\n");
      lines.forEach((l, i) => { if (rx.test(l) && hits.length < 200) hits.push({ file: rel, line: i + 1, text: l.trim().slice(0, 200) }); });
    }
    return hits;
  } });
export const deleteFile = tool({ name: "delete_file", description: "Delete a file.",
  parameters: z.object({ path: z.string() }), execute: async ({ path: p }) => { await fs.unlink(safe(p)); return `deleted ${p}`; } });

export const TOOLS = [readFile, writeFile, appendFile, listDir, searchFiles, deleteFile];
