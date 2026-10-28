import { describe, expect, it } from "vitest";
import { z } from "zod";
import { Agent, tool, type Event } from "../src/index.js";
import { FakeProvider } from "./fake.js";

const add = tool({ name: "add", description: "Add two numbers.", parameters: z.object({ a: z.number(), b: z.number() }), execute: ({ a, b }) => a + b });

describe("tools", () => {
  it("builds a JSON schema from zod", () => {
    const s = add.schema();
    expect(s.name).toBe("add");
    expect((s.parameters as any).properties.a).toEqual({ type: "number" });
    expect((s.parameters as any).required).toEqual(["a", "b"]);
  });
  it("rejects bad arguments", async () => {
    await expect(add.call({ a: "x" })).rejects.toThrow(/Bad arguments/);
  });
});

describe("agent loop", () => {
  it("calls a tool then answers", async () => {
    const p = new FakeProvider([[["add", { a: 2, b: 3 }]], "The answer is 5."]);
    const r = await new Agent("calc", { model: p, tools: [add] }).run("2+3?");
    expect(r.output).toBe("The answer is 5.");
    expect(r.steps).toBe(2);
    expect(r.messages.find((m) => m.role === "tool")?.content).toBe("5");
    expect(String(r)).toBe("The answer is 5.");
  });
  it("feeds unknown-tool errors back to the model", async () => {
    const r = await new Agent("x", { model: new FakeProvider([[["nope", {}]], "ok"]), tools: [add] }).run("hi");
    expect(r.messages.find((m) => m.role === "tool")?.content).toMatch(/unknown tool/);
    expect(r.output).toBe("ok");
  });
  it("captures tool exceptions", async () => {
    const boom = tool({ name: "boom", execute: () => { throw new Error("kaboom"); } });
    const r = await new Agent("x", { model: new FakeProvider([[["boom", {}]], "recovered"]), tools: [boom] }).run("go");
    expect(r.messages.find((m) => m.role === "tool")?.content).toMatch(/kaboom/);
  });
  it("streams events in order", async () => {
    const events: Event[] = [];
    for await (const ev of new Agent("x", { model: new FakeProvider([[["add", { a: 1, b: 1 }]], "2"]), tools: [add] }).stream("1+1")) events.push(ev);
    expect(events.map((e) => e.type)).toEqual(["step_end", "tool_call_start", "tool_call_end", "text_delta", "step_end", "run_end"]);
  });
  it("loads packs by name", async () => {
    const a = new Agent("x", { model: new FakeProvider(["hi"]), tools: ["math", "time"] });
    await a.run("x");
    expect(a.tools.has("calculate")).toBe(true);
    expect(a.tools.has("now")).toBe(true);
  });
  it("runs parallel tool calls", async () => {
    const r = await new Agent("x", { model: new FakeProvider([[["add", { a: 1, b: 1 }], ["add", { a: 2, b: 2 }]], "done"]), tools: [add] }).run("go");
    expect(r.messages.filter((m) => m.role === "tool").map((m) => m.content)).toEqual(["2", "4"]);
  });
  it("hands off between agents", async () => {
    const b = new Agent("I am B", { name: "b", model: new FakeProvider(["hello from b"]) });
    const a = new Agent("route", { name: "a", model: new FakeProvider([[["handoff_to_b", { reason: "lang" }]]]), handoffs: [b] });
    const events: Event[] = [];
    for await (const ev of a.stream("hi")) events.push(ev);
    expect(events.some((e) => e.type === "handoff" && e.toAgent === "b")).toBe(true);
    expect(a.lastResult!.output).toBe("hello from b");
    expect(a.lastResult!.agent).toBe("b");
  });
  it("stops at maxSteps", async () => {
    const script = Array(5).fill([["add", { a: 1, b: 1 }]]);
    const r = await new Agent("x", { model: new FakeProvider([...script, "never"]), tools: [add], maxSteps: 3 }).run("loop");
    expect(r.steps).toBe(3);
  });
});
