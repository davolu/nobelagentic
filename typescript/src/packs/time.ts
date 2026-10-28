import { z } from "zod";
import { tool } from "../tools.js";

export const now = tool({ name: "now", description: "Current date and time in an IANA timezone, e.g. 'Africa/Lagos'.",
  parameters: z.object({ tz: z.string().default("UTC") }),
  execute: ({ tz }) => new Intl.DateTimeFormat("sv-SE", { timeZone: tz, dateStyle: "short", timeStyle: "long" }).format(new Date()) });
export const dateAdd = tool({ name: "date_add", description: "Add days/hours to an ISO date string.",
  parameters: z.object({ date: z.string(), days: z.number().default(0), hours: z.number().default(0) }),
  execute: ({ date, days, hours }) => new Date(new Date(date).getTime() + (days * 24 + hours) * 3600_000).toISOString() });
export const convertTimezone = tool({ name: "convert_timezone", description: "Convert an ISO datetime to another timezone.",
  parameters: z.object({ datetime_iso: z.string(), to_tz: z.string() }),
  execute: ({ datetime_iso, to_tz }) => new Intl.DateTimeFormat("sv-SE", { timeZone: to_tz, dateStyle: "short", timeStyle: "long" }).format(new Date(datetime_iso)) });
export const TOOLS = [now, dateAdd, convertTimezone];
