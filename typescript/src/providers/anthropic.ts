import { Msg, type Message, type ModelResponse, type ToolSchema, type ToolCall, type Usage } from "../types.js";
import { Provider, ProviderError, toolCallFromJson } from "./base.js";

export class AnthropicProvider extends Provider {
  name = "anthropic";
  private client: any;

  constructor(model: string, opts: Record<string, unknown> = {}) {
    super(model, opts);
  }

  private async getClient() {
    if (this.client) return this.client;
    let mod: any;
    try {
      mod = await import("@anthropic-ai/sdk");
    } catch {
      throw new ProviderError("npm install @anthropic-ai/sdk");
    }
    this.client = new mod.default({ apiKey: this.opts.apiKey, baseURL: this.opts.baseUrl });
    return this.client;
  }

  static toApi(messages: Message[]): { system?: string; messages: any[] } {
    let system: string | undefined;
    const out: any[] = [];
    for (const m of messages) {
      if (m.role === "system") system = system ? `${system}\n\n${m.content}` : m.content;
      else if (m.role === "user") out.push({ role: "user", content: m.content });
      else if (m.role === "assistant") {
        const blocks: any[] = [];
        if (m.content) blocks.push({ type: "text", text: m.content });
        for (const tc of m.toolCalls ?? []) blocks.push({ type: "tool_use", id: tc.id, name: tc.name, input: tc.arguments });
        out.push({ role: "assistant", content: blocks.length ? blocks : [{ type: "text", text: "" }] });
      } else {
        const block = { type: "tool_result", tool_use_id: m.toolCallId, content: m.content };
        const last = out[out.length - 1];
        if (last?.role === "user" && Array.isArray(last.content) && last.content[0]?.type === "tool_result") last.content.push(block);
        else out.push({ role: "user", content: [block] });
      }
    }
    return { system, messages: out };
  }

  private static tools(tools: ToolSchema[]) {
    return tools.map((t) => ({ name: t.name, description: t.description, input_schema: t.parameters }));
  }

  async complete(messages: Message[], tools: ToolSchema[], maxTokens = 4096): Promise<ModelResponse> {
    const client = await this.getClient();
    const { system, messages: msgs } = AnthropicProvider.toApi(messages);
    const resp = await client.messages.create({
      model: this.model, max_tokens: maxTokens, messages: msgs,
      ...(system ? { system } : {}), ...(tools.length ? { tools: AnthropicProvider.tools(tools) } : {}),
    });
    let text = "";
    const calls: ToolCall[] = [];
    for (const b of resp.content) {
      if (b.type === "text") text += b.text;
      else if (b.type === "tool_use") calls.push(toolCallFromJson(b.id, b.name, b.input));
    }
    return {
      message: Msg.assistant(text, calls),
      usage: { inputTokens: resp.usage.input_tokens, outputTokens: resp.usage.output_tokens },
      stopReason: calls.length ? "tool_use" : "end", raw: resp,
    };
  }

  async *stream(messages: Message[], tools: ToolSchema[], maxTokens = 4096) {
    const client = await this.getClient();
    const { system, messages: msgs } = AnthropicProvider.toApi(messages);
    const s = client.messages.stream({
      model: this.model, max_tokens: maxTokens, messages: msgs,
      ...(system ? { system } : {}), ...(tools.length ? { tools: AnthropicProvider.tools(tools) } : {}),
    });
    let text = "";
    const calls: ToolCall[] = [];
    let cur: { id: string; name: string; json: string } | null = null;
    const usage: Usage = { inputTokens: 0, outputTokens: 0 };
    for await (const ev of s) {
      if (ev.type === "content_block_start" && ev.content_block.type === "tool_use")
        cur = { id: ev.content_block.id, name: ev.content_block.name, json: "" };
      else if (ev.type === "content_block_delta") {
        if (ev.delta.type === "text_delta") { text += ev.delta.text; yield { text: ev.delta.text }; }
        else if (ev.delta.type === "input_json_delta" && cur) cur.json += ev.delta.partial_json;
      } else if (ev.type === "content_block_stop" && cur) { calls.push(toolCallFromJson(cur.id, cur.name, cur.json)); cur = null; }
      else if (ev.type === "message_start") usage.inputTokens = ev.message.usage.input_tokens;
      else if (ev.type === "message_delta") usage.outputTokens = ev.usage.output_tokens;
    }
    yield { message: Msg.assistant(text, calls), usage, stopReason: calls.length ? "tool_use" : "end" } as ModelResponse;
  }
}
