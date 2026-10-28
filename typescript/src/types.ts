// Provider-neutral message, tool-call and event types.
// Every provider adapter translates to and from these.

export type Role = "system" | "user" | "assistant" | "tool";

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface Message {
  role: Role;
  content: string;
  toolCalls?: ToolCall[];
  toolCallId?: string; // for role === "tool"
  name?: string;
}

export const Msg = {
  system: (content: string): Message => ({ role: "system", content }),
  user: (content: string): Message => ({ role: "user", content }),
  assistant: (content = "", toolCalls: ToolCall[] = []): Message => ({ role: "assistant", content, toolCalls }),
  tool: (callId: string, name: string, result: string): Message => ({ role: "tool", content: result, toolCallId: callId, name }),
};

export interface Usage {
  inputTokens: number;
  outputTokens: number;
}
export const addUsage = (a: Usage, b: Usage): Usage => ({
  inputTokens: a.inputTokens + b.inputTokens,
  outputTokens: a.outputTokens + b.outputTokens,
});

export interface ModelResponse {
  message: Message;
  usage: Usage;
  stopReason: "end" | "tool_use" | "max_tokens";
  raw?: unknown;
}

// Stream events — identical names to the Python package.
export type Event =
  | { type: "text_delta"; text: string }
  | { type: "tool_call_start"; call: ToolCall }
  | { type: "tool_call_end"; call: ToolCall; result: string; error: boolean }
  | { type: "step_end"; step: number; usage: Usage }
  | { type: "handoff"; fromAgent: string; toAgent: string; reason: string }
  | { type: "run_end"; output: string; usage: Usage; steps: number };

export interface RunResult {
  output: string;
  messages: Message[];
  usage: Usage;
  steps: number;
  agent: string;
  toString(): string;
}

export interface ToolSchema {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}
