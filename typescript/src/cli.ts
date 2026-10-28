#!/usr/bin/env node
// nobelagentic run "..." | chat | tools list | mcp list|add
import { createInterface } from "node:readline/promises";
import { Agent } from "./agent.js";
import type { Message } from "./types.js";

const SAFE = "web,time,math,data";
const args = process.argv.slice(2);
const flag = (n: string) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : undefined; };
const dim = (s: string) => `\x1b[2m${s}\x1b[0m`;

function build() {
  return new Agent(flag("instructions") ?? "You are a helpful assistant. Use tools when they help.", {
    model: flag("model"),
    tools: (flag("tools") ?? SAFE).split(",").filter(Boolean),
    mcp: (flag("mcp") ?? "").split(",").filter(Boolean),
  });
}

async function streamOut(agent: Agent, text: string, history?: Message[]) {
  for await (const ev of agent.stream(text, { history })) {
    if (ev.type === "text_delta") process.stdout.write(ev.text);
    else if (ev.type === "tool_call_start") console.log(dim(`\n→ ${ev.call.name}(${JSON.stringify(ev.call.arguments).slice(0, 120)})`));
    else if (ev.type === "tool_call_end") console.log(dim(`${ev.error ? "✗" : "✓"} ${ev.result.slice(0, 160)}`));
    else if (ev.type === "handoff") console.log(`\n↪ ${ev.fromAgent} → ${ev.toAgent}`);
    else if (ev.type === "run_end") console.log(dim(`\n${ev.steps} steps · ${ev.usage.inputTokens}+${ev.usage.outputTokens} tokens`));
  }
}

async function main() {
  const [cmd, sub] = args;
  if (cmd === "run") return streamOut(build(), args.filter((a, i) => i > 0 && !a.startsWith("--") && !args[i - 1]?.startsWith("--")).join(" "));
  if (cmd === "chat") {
    const agent = build();
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    let history: Message[] = [];
    for (;;) {
      const text = await rl.question("you › ");
      if (["exit", "quit", "/q"].includes(text.trim())) break;
      await streamOut(agent, text, history);
      history = agent.lastResult!.messages.filter((m) => m.role !== "system");
      console.log();
    }
    rl.close(); return;
  }
  if (cmd === "tools" && sub === "list") {
    const { allTools } = await import("./packs/index.js");
    for (const [pack, tools] of Object.entries(await allTools())) { console.log(`\n${pack}`); for (const t of tools) console.log(`  ${t.name.padEnd(18)} ${t.description}`); }
    return;
  }
  if (cmd === "mcp" && sub === "list") {
    const { REGISTRY } = await import("./mcp.js");
    for (const [n, c] of Object.entries(REGISTRY)) console.log(`${n.padEnd(12)} ${[c.command, ...((c.args as string[]) ?? [])].join(" ")}`);
    return;
  }
  if (cmd === "mcp" && sub === "add") {
    const { addServer } = await import("./mcp.js");
    const [name, command] = [args[2], args.slice(3).join(" ")];
    await addServer(name, command.startsWith("http") ? { url: command } : { command: command.split(" ")[0], args: command.split(" ").slice(1) });
    console.log(`added ${name}`); return;
  }
  console.log(`nobelagentic — agents that get out of your way

  nobelagentic run "<prompt>" [--tools web,files] [--model gpt-5] [--mcp github]
  nobelagentic chat
  nobelagentic tools list
  nobelagentic mcp list | mcp add <name> <command...>`);
}
main().catch((e) => { console.error(e.message ?? e); process.exit(1); });
