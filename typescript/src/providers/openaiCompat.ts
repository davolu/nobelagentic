// One adapter for every chat.completions-dialect host: OpenAI, Gemini, Ollama, Groq, OpenRouter, Together.
import { Msg, type Message, type ModelResponse, type ToolSchema, type ToolCall, type Usage } from "../types.js";
import { Provider, ProviderError, toolCallFromJson } from "./base.js";

const VENDORS: Record<string, [string | null, string | undefined]> = {
  openai: ["OPENAI_API_KEY", undefined],
  gemini: ["GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/"],
  ollama: [null, "http://localhost:11434/v1"],
  groq: ["GROQ_API_KEY", "https://api.groq.com/openai/v1"],
  openrouter: ["OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"],
  together: ["TOGETHER_API_KEY", "https://api.together.xyz/v1"],
};

export class OpenAICompatProvider extends Provider {
  private client: any;
  constructor(model: string, public vendor = "openai", opts: Record<string, unknown> = {}) {
    super(model, opts);
    this.name = vendor;
  }

  private async getClient() {
    if (this.client) return this.client;
    let mod: any;
    try { mod = await import("openai"); } catch { throw new ProviderError("npm install openai"); }
    const [envVar, baseURL] = VENDORS[this.vendor];
    const apiKey = (this.opts.apiKey as string) ?? (envVar ? process.env[envVar] : "ollama");
    if (!apiKey) throw new ProviderError(`${this.vendor}: set ${envVar} or pass apiKey`);
    this.client = new mod.default({ apiKey, baseURL: (this.opts.baseUrl as string) ?? baseURL });
    return this.client;
  }

  static toApi(messages: Message[]): any[] {
    return messages.map((m) => {
      if (m.role === "assistant") return {
        role: "assistant", content: m.content || null,
        ...(m.toolCalls?.length ? { tool_calls: m.toolCalls.map((tc) => ({
          id: tc.id, type: "function", function: { name: tc.name, arguments: JSON.stringify(tc.arguments) } })) } : {}),
      };
      if (m.role === "tool") return { role: "tool", tool_call_id: m.toolCallId, content: m.content };
      return { role: m.role, content: m.content };
    });
  }

  private static tools(tools: ToolSchema[]) {
    return tools.map((t) => ({ type: "function", function: { name: t.name, description: t.description, parameters: t.parameters } }));
  }

  async complete(messages: Message[], tools: ToolSchema[], maxTokens = 4096): Promise<ModelResponse> {
    const client = await this.getClient();
    const resp = await client.chat.completions.create({
      model: this.model, messages: OpenAICompatProvider.toApi(messages), max_tokens: maxTokens,
      ...(tools.length ? { tools: OpenAICompatProvider.tools(tools) } : {}),
    });
    const c = resp.choices[0];
    const calls: ToolCall[] = (c.message.tool_calls ?? []).map((tc: any) => toolCallFromJson(tc.id, tc.function.name, tc.function.arguments));
    return {
      message: Msg.assistant(c.message.content ?? "", calls),
      usage: { inputTokens: resp.usage?.prompt_tokens ?? 0, outputTokens: resp.usage?.completion_tokens ?? 0 },
      stopReason: calls.length ? "tool_use" : "end", raw: resp,
    };
  }

  async *stream(messages: Message[], tools: ToolSchema[], maxTokens = 4096) {
    const client = await this.getClient();
    const s = await client.chat.completions.create({
      model: this.model, messages: OpenAICompatProvider.toApi(messages), max_tokens: maxTokens,
      stream: true, stream_options: { include_usage: true },
      ...(tools.length ? { tools: OpenAICompatProvider.tools(tools) } : {}),
    });
    let text = "";
    const partial = new Map<number, { id: string; name: string; args: string }>();
    let usage: Usage = { inputTokens: 0, outputTokens: 0 };
    for await (const chunk of s) {
      if (chunk.usage) usage = { inputTokens: chunk.usage.prompt_tokens, outputTokens: chunk.usage.completion_tokens };
      const d = chunk.choices?.[0]?.delta;
      if (!d) continue;
      if (d.content) { text += d.content; yield { text: d.content }; }
      for (const tc of d.tool_calls ?? []) {
        const slot = partial.get(tc.index) ?? { id: "", name: "", args: "" };
        if (tc.id) slot.id = tc.id;
        if (tc.function?.name) slot.name += tc.function.name;
        if (tc.function?.arguments) slot.args += tc.function.arguments;
        partial.set(tc.index, slot);
      }
    }
    const calls = [...partial.entries()].sort((a, b) => a[0] - b[0]).map(([, p]) => toolCallFromJson(p.id, p.name, p.args));
    yield { message: Msg.assistant(text, calls), usage, stopReason: calls.length ? "tool_use" : "end" } as ModelResponse;
  }
}
