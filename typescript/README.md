# Swarm Agents (TypeScript)

**Agents that get out of your way.** One kernel, three APIs, any model. Same API as the Python package.

```ts
import { Agent, tool, z } from "swarmagents";

const getWeather = tool({
  name: "get_weather",
  description: "Current weather for a city",
  parameters: z.object({ city: z.string() }),
  execute: ({ city }) => `${city}: 31°C, humid`,
});

const agent = new Agent("You help plan trips", { tools: [getWeather, "web", "time"] });
console.log(await agent.run("What's the weather in Lagos right now?"));
```

## Install

```bash
npm install swarmagents @anthropic-ai/sdk     # or openai
```

Set `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`, or use `model: "ollama:llama3.1"`.

## Tools

A `zod` schema plus a function. The schema *is* the documentation the model sees.

```ts
new Agent("...", { tools: [myTool, "web", "files"] })   // own tools + built-in packs
```

Packs: `web` `files` `shell` `time` `math` `data` (`shell` is opt-in).

## MCP

```ts
new Agent("...", { mcp: ["github", "https://my-server.example.com/mcp"] })
```

## Streaming

```ts
for await (const ev of agent.stream("...")) {
  if (ev.type === "text_delta") process.stdout.write(ev.text);
  if (ev.type === "tool_call_start") console.log("calling", ev.call.name);
}
```

## Handoffs

```ts
const spanish = new Agent("You only speak Spanish", { name: "spanish" });
const triage  = new Agent("Route by language", { handoffs: [spanish] });
await triage.run("Hola!");
```

## CLI

```
npx swarmagents run "What is 15% of 240?"
npx swarmagents chat --tools web,files --mcp github
npx swarmagents tools list
```

## Develop

```bash
npm install && npm test && npm run build
```
