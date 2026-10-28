// Agent: the one-liner API. Same ReAct loop and same events as the Python package.
import { resolve, Provider } from "./providers/base.js";
import { tool, ToolError, type Tool } from "./tools.js";
import { addUsage, Msg, type Event, type Message, type ModelResponse, type RunResult, type ToolCall, type Usage } from "./types.js";
import { z } from "zod";

export interface AgentOptions {
  name?: string;
  model?: string | Provider;
  tools?: (Tool | string)[];
  mcp?: (string | Record<string, unknown>)[];
  handoffs?: Agent[];
  maxSteps?: number;
  maxTokens?: number;
  parallelTools?: boolean;
  onEvent?: (ev: Event) => void;
}

export class Agent {
  name: string;
  instructions: string;
  tools = new Map<string, Tool>();
  handoffs = new Map<string, Agent>();
  maxSteps: number;
  maxTokens: number;
  parallelTools: boolean;
  onEvent?: (ev: Event) => void;
  lastResult?: RunResult;
  private modelSpec?: string | Provider;
  private providerInstance?: Provider;
  private mcpSpecs: (string | Record<string, unknown>)[];
  private pendingPacks: string[] = [];
  private ready = false;

  constructor(instructions = "You are a helpful assistant.", opts: AgentOptions = {}) {
    this.name = opts.name ?? "agent";
    this.instructions = instructions;
    this.modelSpec = opts.model;
    this.maxSteps = opts.maxSteps ?? 25;
    this.maxTokens = opts.maxTokens ?? 4096;
    this.parallelTools = opts.parallelTools ?? true;
    this.onEvent = opts.onEvent;
    this.mcpSpecs = opts.mcp ?? [];
    for (const t of opts.tools ?? []) this.addTool(t);
    for (const a of opts.handoffs ?? []) {
      this.handoffs.set(a.name, a);
      this.addTool(this.handoffTool(a));
    }
  }

  async provider(): Promise<Provider> {
    return (this.providerInstance ??= await resolve(this.modelSpec));
  }

  addTool(t: Tool | string): void {
    if (typeof t === "string") { this.pendingPacks.push(t); this.ready = false; return; }
    const missing = (t.requires ?? []).filter((v) => !process.env[v]);
    if (missing.length) throw new ToolError(`Tool '${t.name}' needs env var(s): ${missing.join(", ")}`);
    this.tools.set(t.name, t);
  }

  private handoffTool(target: Agent): Tool {
    return tool({
      name: `handoff_to_${target.name}`,
      description: `Hand the conversation to the '${target.name}' agent. ${target.instructions.slice(0, 120)}`,
      parameters: z.object({ reason: z.string().optional() }),
      execute: ({ reason }) => `__handoff__:${target.name}:${reason ?? ""}`,
    });
  }

  /** Expose this agent as a tool, so an orchestrator agent can delegate to it.
   *  Unlike a handoff (which transfers the conversation), the caller stays in
   *  control: it gets the result back and can combine it with other work. */
  asTool(opts: { name?: string; description?: string } = {}): Tool {
    return tool({
      name: opts.name ?? `ask_${this.name}`,
      description: opts.description ?? `Delegate a task to the '${this.name}' agent and get its answer back. ${this.instructions.slice(0, 120)}`,
      parameters: z.object({ task: z.string() }),
      execute: async ({ task }) => (await this.run(task)).output,
    });
  }

  private async setup(): Promise<void> {
    if (this.ready) return;
    if (this.pendingPacks.length) {
      const { loadPack } = await import("./packs/index.js");
      for (const p of this.pendingPacks) for (const t of await loadPack(p)) this.tools.set(t.name, t);
      this.pendingPacks = [];
    }
    if (this.mcpSpecs.length) {
      const { connect } = await import("./mcp.js");
      for (const s of this.mcpSpecs) for (const t of await connect(s)) this.tools.set(t.name, t);
      this.mcpSpecs = [];
    }
    this.ready = true;
  }

  async run(input: string | Message[], opts?: { history?: Message[] }): Promise<RunResult> {
    for await (const _ of this.stream(input, opts)) { /* drain */ }
    return this.lastResult!;
  }

  async *stream(input: string | Message[], opts: { history?: Message[] } = {}): AsyncGenerator<Event> {
    await this.setup();
    const messages: Message[] = [Msg.system(this.instructions), ...(opts.history ?? []),
      ...(typeof input === "string" ? [Msg.user(input)] : input)];
    let total: Usage = { inputTokens: 0, outputTokens: 0 };
    let steps = 0;
    let agent: Agent = this;

    while (steps < agent.maxSteps) {
      steps++;
      await agent.setup();
      const schemas = [...agent.tools.values()].map((t) => t.schema());
      const provider = await agent.provider();
      let response: ModelResponse | undefined;
      for await (const chunk of provider.stream(messages, schemas, agent.maxTokens)) {
        if ("text" in chunk && !("message" in chunk)) yield this.emit({ type: "text_delta", text: chunk.text });
        else response = chunk as ModelResponse;
      }
      if (!response) throw new Error("provider produced no response");
      total = addUsage(total, response.usage);
      messages.push(response.message);
      yield this.emit({ type: "step_end", step: steps, usage: response.usage });

      const calls = response.message.toolCalls ?? [];
      if (!calls.length) break;
      for (const c of calls) yield this.emit({ type: "tool_call_start", call: c });
      const results = agent.parallelTools
        ? await Promise.all(calls.map((c) => agent.exec(c)))
        : await calls.reduce(async (acc, c) => [...(await acc), await agent.exec(c)], Promise.resolve([] as [string, boolean][]));

      let handoff: Agent | undefined;
      for (let i = 0; i < calls.length; i++) {
        const call = calls[i];
        const [text, isErr] = results[i];
        yield this.emit({ type: "tool_call_end", call, result: text, error: isErr });
        messages.push(Msg.tool(call.id, call.name, text));
        if (text.startsWith("__handoff__:")) {
          const [, target, ...rest] = text.split(":");
          handoff = agent.handoffs.get(target);
          yield this.emit({ type: "handoff", fromAgent: agent.name, toAgent: target, reason: rest.join(":") });
        }
      }
      if (handoff) {
        agent = handoff;
        messages[0] = Msg.system(agent.instructions);
      }
    }

    const output = [...messages].reverse().find((m) => m.role === "assistant" && m.content)?.content ?? "";
    this.lastResult = { output, messages, usage: total, steps, agent: agent.name, toString: () => output };
    yield this.emit({ type: "run_end", output, usage: total, steps });
  }

  private async exec(call: ToolCall): Promise<[string, boolean]> {
    const t = this.tools.get(call.name);
    if (!t) return [`Error: unknown tool '${call.name}'. Available: ${[...this.tools.keys()].join(", ")}`, true];
    try {
      return [await t.call(call.arguments), false];
    } catch (e: any) {
      return [`Error from ${call.name}: ${e?.name ?? "Error"}: ${e?.message ?? e}`, true];
    }
  }

  private emit(ev: Event): Event {
    this.onEvent?.(ev);
    return ev;
  }
}
