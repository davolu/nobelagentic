import { Provider } from "../src/providers/base.js";
import { Msg, type Message, type ModelResponse } from "../src/types.js";

export type Step = string | [string, Record<string, unknown>][];
export class FakeProvider extends Provider {
  name = "fake";
  seen: Message[][] = [];
  constructor(public script: Step[]) { super("fake-1"); }
  async complete(messages: Message[]): Promise<ModelResponse> {
    this.seen.push([...messages]);
    const step = this.script.shift()!;
    const usage = { inputTokens: 10, outputTokens: 5 };
    if (typeof step === "string") return { message: Msg.assistant(step), usage, stopReason: "end" };
    return { message: Msg.assistant("", step.map(([name, a], i) => ({ id: `c${i}`, name, arguments: a }))), usage, stopReason: "tool_use" };
  }
}
