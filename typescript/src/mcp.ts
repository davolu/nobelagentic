// MCP client: any MCP server becomes a set of tools.
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { rawTool, ToolError, type Tool } from "./tools.js";

export const REGISTRY: Record<string, Record<string, unknown>> = {
  filesystem: { command: "npx", args: ["-y", "@modelcontextprotocol/server-filesystem", "."] },
  github: { command: "npx", args: ["-y", "@modelcontextprotocol/server-github"], env: ["GITHUB_PERSONAL_ACCESS_TOKEN"] },
  postgres: { command: "npx", args: ["-y", "@modelcontextprotocol/server-postgres"], env: ["DATABASE_URL"] },
  playwright: { command: "npx", args: ["-y", "@playwright/mcp@latest"] },
  fetch: { command: "uvx", args: ["mcp-server-fetch"] },
  memory: { command: "npx", args: ["-y", "@modelcontextprotocol/server-memory"] },
  slack: { command: "npx", args: ["-y", "@modelcontextprotocol/server-slack"], env: ["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"] },
};
const CONFIG = path.join(os.homedir(), ".nobelagentic", "mcp.json");

async function userServers(): Promise<Record<string, Record<string, unknown>>> {
  try { return JSON.parse(await fs.readFile(CONFIG, "utf8")).servers ?? {}; } catch { return {}; }
}

async function resolveSpec(spec: string | Record<string, unknown>): Promise<Record<string, unknown>> {
  if (typeof spec !== "string") return spec;
  if (/^https?:\/\//.test(spec)) return { url: spec };
  const user = await userServers();
  if (user[spec]) return user[spec];
  if (REGISTRY[spec]) return REGISTRY[spec];
  throw new ToolError(`Unknown MCP server '${spec}'. Known: ${Object.keys(REGISTRY).join(", ")}; or add it with \`nobelagentic mcp add\`.`);
}

export async function connect(spec: string | Record<string, unknown>): Promise<Tool[]> {
  let sdk: any, stdio: any, http: any;
  try {
    sdk = await import("@modelcontextprotocol/sdk/client/index.js");
    stdio = await import("@modelcontextprotocol/sdk/client/stdio.js");
    http = await import("@modelcontextprotocol/sdk/client/streamableHttp.js");
  } catch { throw new ToolError("npm install @modelcontextprotocol/sdk"); }
  const cfg = await resolveSpec(spec);
  for (const v of (cfg.env as string[]) ?? []) if (!process.env[v]) throw new ToolError(`MCP server needs env var ${v}`);
  const client = new sdk.Client({ name: "nobelagentic", version: "0.1.0" });
  const transport = cfg.url
    ? new http.StreamableHTTPClientTransport(new URL(cfg.url as string))
    : new stdio.StdioClientTransport({ command: cfg.command, args: cfg.args ?? [], env: { ...process.env, ...((cfg.env_values as any) ?? {}) } });
  await client.connect(transport);
  const label = typeof spec === "string" ? spec : String(cfg.command ?? "mcp");
  const { tools } = await client.listTools();
  return tools.map((t: any) => rawTool({
    name: t.name, description: t.description ?? t.name, jsonSchema: t.inputSchema ?? { type: "object", properties: {} }, pack: `mcp:${label}`,
    execute: async (args) => {
      const res: any = await client.callTool({ name: t.name, arguments: args });
      const out = (res.content ?? []).map((c: any) => c.text ?? JSON.stringify(c)).join("\n");
      return res.isError ? `Error: ${out}` : out;
    },
  }));
}

export async function addServer(name: string, cfg: Record<string, unknown>): Promise<void> {
  await fs.mkdir(path.dirname(CONFIG), { recursive: true });
  const data = { servers: await userServers() };
  data.servers[name] = cfg;
  await fs.writeFile(CONFIG, JSON.stringify(data, null, 2));
}
