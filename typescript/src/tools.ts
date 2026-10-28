// Tools: a zod schema + a function. zod is the TS equivalent of Python type hints.
//
//   const getWeather = tool({
//     name: "get_weather",
//     description: "Current weather for a city",
//     parameters: z.object({ city: z.string() }),
//     execute: async ({ city }) => `${city}: 31°C`,
//   });

import { z, type ZodTypeAny } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";
import type { ToolSchema } from "./types.js";

export class ToolError extends Error {}

export interface Tool {
  name: string;
  description: string;
  parameters: ZodTypeAny;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  execute: (args: any) => unknown | Promise<unknown>;
  pack?: string;
  requires?: string[];
  schema(): ToolSchema;
  call(args: Record<string, unknown>): Promise<string>;
}

export function tool<P extends ZodTypeAny>(def: {
  name: string;
  description?: string;
  parameters?: P;
  execute: (args: z.infer<P>) => unknown | Promise<unknown>;
  pack?: string;
  requires?: string[];
}): Tool {
  const parameters: ZodTypeAny = def.parameters ?? z.object({});
  const t: Tool = {
    name: def.name,
    description: def.description ?? def.name.replace(/_/g, " "),
    parameters,
    execute: def.execute,
    pack: def.pack,
    requires: def.requires ?? [],
    schema() {
      const js = zodToJsonSchema(parameters, { $refStrategy: "none" }) as Record<string, unknown>;
      delete js.$schema;
      return { name: t.name, description: t.description, parameters: js };
    },
    async call(args) {
      const parsed = parameters.safeParse(args);
      if (!parsed.success) throw new ToolError(`Bad arguments for ${t.name}: ${parsed.error.message}`);
      return stringify(await t.execute(parsed.data));
    },
  };
  return t;
}

export function stringify(v: unknown): string {
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

// Raw tool from an existing JSON schema (used by MCP).
export function rawTool(def: {
  name: string;
  description: string;
  jsonSchema: Record<string, unknown>;
  execute: (args: Record<string, unknown>) => Promise<string>;
  pack?: string;
}): Tool {
  return {
    name: def.name,
    description: def.description,
    parameters: z.any(),
    execute: def.execute,
    pack: def.pack,
    requires: [],
    schema: () => ({ name: def.name, description: def.description, parameters: def.jsonSchema }),
    call: (args) => def.execute(args),
  };
}
