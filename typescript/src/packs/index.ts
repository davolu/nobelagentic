import type { Tool } from "../tools.js";

export const PACKS: Record<string, () => Promise<{ TOOLS: Tool[] }>> = {
  web: () => import("./web.js"),
  files: () => import("./files.js"),
  shell: () => import("./shell.js"),
  time: () => import("./time.js"),
  math: () => import("./math.js"),
  data: () => import("./data.js"),
};

export async function loadPack(name: string): Promise<Tool[]> {
  const loader = PACKS[name];
  if (!loader) throw new Error(`Unknown tool pack '${name}'. Available: ${Object.keys(PACKS).join(", ")}`);
  const tools = (await loader()).TOOLS;
  for (const t of tools) t.pack = name;
  return tools;
}

export async function allTools(): Promise<Record<string, Tool[]>> {
  const out: Record<string, Tool[]> = {};
  for (const name of Object.keys(PACKS)) out[name] = await loadPack(name);
  return out;
}
