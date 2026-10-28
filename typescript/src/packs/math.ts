import { z } from "zod";
import { tool } from "../tools.js";

const FUNCS: Record<string, (...a: number[]) => number> = { sqrt: Math.sqrt, abs: Math.abs, round: Math.round, floor: Math.floor, ceil: Math.ceil,
  sin: Math.sin, cos: Math.cos, tan: Math.tan, log: Math.log, log10: Math.log10, exp: Math.exp, min: Math.min, max: Math.max, pow: Math.pow };
export const calculate = tool({ name: "calculate", description: "Evaluate a math expression safely, e.g. 'sqrt(2) * 10 ** 3'.",
  parameters: z.object({ expression: z.string() }),
  execute: ({ expression }) => {
    if (!/^[\d\s+\-*/%().,a-z]+$/i.test(expression)) throw new Error("Unsupported characters in expression");
    const names = expression.match(/[a-z]+/gi) ?? [];
    for (const n of names) if (!(n in FUNCS) && n !== "pi" && n !== "e") throw new Error(`Unknown function ${n}`);
    return new Function(...Object.keys(FUNCS), "pi", "e", `return (${expression})`)(...Object.values(FUNCS), Math.PI, Math.E) as number;
  } });
const UNITS: Record<string, number> = { km: 1000, m: 1, cm: 0.01, mi: 1609.344, ft: 0.3048, in: 0.0254, kg: 1, g: 0.001, lb: 0.45359237, oz: 0.028349523, l: 1, ml: 0.001, gal: 3.785411784 };
export const convertUnits = tool({ name: "convert_units", description: "Convert between common length, mass, volume and temperature units.",
  parameters: z.object({ value: z.number(), from_unit: z.string(), to_unit: z.string() }),
  execute: ({ value, from_unit, to_unit }) => {
    const f = from_unit.toLowerCase(), t = to_unit.toLowerCase();
    if ((f === "c" || f === "f") && (t === "c" || t === "f")) return f === t ? value : f === "c" ? value * 9 / 5 + 32 : (value - 32) * 5 / 9;
    return (value * UNITS[f]) / UNITS[t];
  } });
export const TOOLS = [calculate, convertUnits];
