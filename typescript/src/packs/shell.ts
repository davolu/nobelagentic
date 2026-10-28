import { z } from "zod";
import { exec } from "node:child_process";
import { tool } from "../tools.js";

export const runCommand = tool({
  name: "run_command", description: "Run a shell command and return stdout, stderr and exit code.",
  parameters: z.object({ command: z.string(), timeout: z.number().int().default(60) }),
  execute: ({ command, timeout }) => new Promise((res) => {
    exec(command, { timeout: timeout * 1000, maxBuffer: 10_000_000 }, (err, stdout, stderr) =>
      res({ stdout: stdout.slice(-8000), stderr: stderr.slice(-4000), code: err && "code" in err ? (err as any).code : 0 }));
  }),
});
export const runJavascript = tool({
  name: "run_javascript", description: "Execute JavaScript in-process and return the result or console output.",
  parameters: z.object({ code: z.string() }),
  execute: async ({ code }) => {
    const logs: string[] = []; const c = { log: (...a: unknown[]) => logs.push(a.map(String).join(" ")) };
    try { const r = await new Function("console", `return (async()=>{${code}})()`)(c); return logs.join("\n") || (r === undefined ? "(no output)" : String(r)); }
    catch (e: any) { return `${e.name}: ${e.message}`; }
  },
});
export const TOOLS = [runCommand, runJavascript];
