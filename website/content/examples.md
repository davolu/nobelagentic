---
title: Examples
nav: Examples
order: 7
---
# Building real agents

Recipes for the question everyone asks next: *"OK, but how do I ship something useful?"*
Every example below uses only the public API — `Agent`, `@tool`, `handoffs`, `mcp` — glued to the outside world with ordinary webhook code.

## A WhatsApp agent

NobelAgentic doesn't care where messages come from. Point any webhook at an `Agent` and reply with the result. Here's a WhatsApp support agent using the [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) and FastAPI:

```python
import os, httpx
from fastapi import FastAPI, Request
from nobelagentic import Agent, tool

@tool
def order_status(order_id: str) -> dict:
    """Look up an order's status and ETA by its ID."""
    r = httpx.get(f"https://api.yourshop.com/orders/{order_id}",
                  headers={"Authorization": f"Bearer {os.environ['SHOP_API_KEY']}"})
    return r.json()

agent = Agent(
    "You are the support agent for YourShop. Be warm and brief — "
    "answers go to WhatsApp, so no markdown, short paragraphs.",
    tools=[order_status, "time"],
)

app = FastAPI()
WA_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_ID = os.environ["WHATSAPP_PHONE_ID"]

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
    reply = agent.run(msg["text"]["body"])
    httpx.post(
        f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        json={"messaging_product": "whatsapp", "to": msg["from"],
              "text": {"body": str(reply)}},
    )
    return {"status": "ok"}
```

That's the whole bot. The same shape works for Telegram, Slack, Discord, SMS via Twilio — swap the webhook parsing and the send call.

## Any third-party API as a tool

A tool is just a function. Type hints and the docstring become the schema the model sees, so wrapping any SDK or REST API is one decorator:

```python
import httpx
from nobelagentic import Agent, tool

@tool
def search_crm(query: str) -> list:
    """Search customers in the CRM by name or email."""
    return httpx.get("https://api.crm.example.com/search",
                     params={"q": query}).json()

@tool
async def create_ticket(title: str, body: str, priority: str = "normal") -> dict:
    """Open a support ticket. Priority: low, normal, or urgent."""
    async with httpx.AsyncClient() as c:
        r = await c.post("https://api.ticketing.example.com/tickets",
                         json={"title": title, "body": body, "priority": priority})
        return r.json()

agent = Agent("You handle inbound support requests end to end.",
              tools=[search_crm, create_ticket])

agent.run("jane@acme.co says checkout is broken — file an urgent ticket")
```

Sync and async functions both work. Raise an exception and the model sees the error message and can recover.

## A support team with handoffs

Split responsibilities across agents and let a triage agent route:

```python
from nobelagentic import Agent

billing = Agent("You resolve billing questions. You can issue refunds up to $50.",
                name="billing", tools=[search_crm, "math"])
tech    = Agent("You debug technical issues. Ask for error messages early.",
                name="tech", tools=[create_ticket, "web"])

triage = Agent(
    "Classify the user's problem and hand off to billing or tech immediately. "
    "Never answer yourself.",
    name="triage",
    handoffs=[billing, tech],
)

result = triage.run("I was charged twice for my subscription this month")
print(result.agent, "→", result.output)   # billing → ...
```

## Third-party services via MCP

Anything with an MCP server — GitHub, Postgres, Stripe, your own internal tools — plugs in without writing a wrapper:

```python
Agent("You triage bug reports into GitHub issues.",
      mcp=["github"])                                  # registry name

Agent("You answer questions about our production data. Read-only.",
      mcp=["postgres"])

Agent("...", mcp=["https://mcp.yourcompany.com/mcp"])  # any remote server
```

Register a server once with `nobelagentic mcp add myserver "npx -y some-mcp-server"` and every project can use it by name.

## TypeScript: a Telegram bot

The TypeScript package has the same API. A long-polling Telegram bot, no framework needed:

```ts
import { Agent, tool, z } from "nobelagentic";

const fx = tool({
  name: "fx_rate",
  description: "Current exchange rate between two currencies",
  parameters: z.object({ from: z.string(), to: z.string() }),
  execute: async ({ from, to }) =>
    (await fetch(`https://api.frankfurter.app/latest?from=${from}&to=${to}`)).json(),
});

const agent = new Agent("You are a concise personal finance assistant.", {
  tools: [fx, "math", "time"],
});

const API = `https://api.telegram.org/bot${process.env.TELEGRAM_TOKEN}`;
let offset = 0;
while (true) {
  const { result } = await (await fetch(`${API}/getUpdates?timeout=30&offset=${offset}`)).json();
  for (const u of result) {
    offset = u.update_id + 1;
    if (!u.message?.text) continue;
    const reply = await agent.run(u.message.text);
    await fetch(`${API}/sendMessage`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: u.message.chat.id, text: String(reply) }),
    });
  }
}
```

## Keeping context between messages

Chat platforms deliver one message at a time. Every run accepts `history=` — the full typed transcript, tool calls included — and returns the updated one on the result:

```python
sessions: dict[str, list] = {}          # user_id → message history

def handle(user_id: str, text: str) -> str:
    result = agent.run(text, history=sessions.get(user_id))
    sessions[user_id] = [m for m in result.messages if m.role != "system"]
    return str(result)
```

Swap the dict for Redis in production and you have a stateful bot today. First-class sessions — `agent.run(text, session="user-123")` with pluggable storage — land in v0.2 (see the [roadmap](roadmap.html)).
