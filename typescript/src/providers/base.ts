import type { Message, ModelResponse, ToolCall, ToolSchema } from "../types.js";

export abstract class Provider {
  name = "base";
  constructor(public model: string, public opts: Record<string, unknown> = {}) {}

  abstract complete(messages: Message[], tools: ToolSchema[], maxTokens?: number): Promise<ModelResponse>;

  // Default streaming: fake deltas from complete(). Adapters override.
  async *stream(messages: Message[], tools: ToolSchema[], maxTokens = 4096): AsyncGenerator<{ text: string } | ModelResponse> {
    const r = await this.complete(messages, tools, maxTokens);
    if (r.message.content) yield { text: r.message.content };
    yield r;
  }
}

export class ProviderError extends Error {}

const PREFIXES: Record<string, string> = {
  claude: "anthropic", gpt: "openai", o1: "openai", o3: "openai", o4: "openai",
  gemini: "gemini", llama: "ollama", mistral: "ollama", qwen: "ollama", phi: "ollama",
};
const DEFAULTS: Record<string, [string | null, string]> = {
  anthropic: ["ANTHROPIC_API_KEY", "claude-sonnet-5-5"],
  openai: ["OPENAI_API_KEY", "gpt-5"],
  gemini: ["GEMINI_API_KEY", "gemini-2.5-pro"],
  ollama: [null, "llama3.1"],
};
const env = (k: string) => (typeof process !== "undefined" ? process.env[k] : undefined) || undefined;

export async function resolve(model?: string | Provider, opts: Record<string, unknown> = {}): Promise<Provider> {
  if (model instanceof Provider) return model;
  let providerName: string | undefined;
  let modelName = model;
  if (model && model.includes(":") && !model.startsWith("http")) {
    [providerName, modelName] = [model.slice(0, model.indexOf(":")), model.slice(model.indexOf(":") + 1)];
  } else if (model) {
    providerName = Object.entries(PREFIXES).find(([p]) => model.toLowerCase().startsWith(p))?.[1] ?? "openai";
  } else {
    for (const [p, [envVar, def]] of Object.entries(DEFAULTS)) {
      if (envVar && env(envVar)) { providerName = p; modelName = def; break; }
    }
    if (!providerName) throw new ProviderError(
      "No model configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY or GEMINI_API_KEY, or pass model: 'ollama:llama3.1'.");
  }
  modelName = modelName || DEFAULTS[providerName]?.[1];
  if (providerName === "anthropic") {
    const { AnthropicProvider } = await import("./anthropic.js");
    return new AnthropicProvider(modelName!, opts);
  }
  if (["openai", "gemini", "ollama", "groq", "openrouter", "together"].includes(providerName)) {
    const { OpenAICompatProvider } = await import("./openaiCompat.js");
    return new OpenAICompatProvider(modelName!, providerName, opts);
  }
  throw new ProviderError(`Unknown provider '${providerName}'.`);
}

export function toolCallFromJson(id: string, name: string, args: string | Record<string, unknown>): ToolCall {
  if (typeof args !== "string") return { id, name, arguments: args };
  try {
    return { id, name, arguments: args.trim() ? JSON.parse(args) : {} };
  } catch {
    return { id, name, arguments: { _raw: args } };
  }
}
