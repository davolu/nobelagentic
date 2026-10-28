---
title: Tools
nav: Tools
order: 2
---
# Tools

A tool is a function the model can call. You never write a JSON schema.

## Your own tools

Python builds the schema from type hints and the docstring. An `Args:` block becomes per-parameter descriptions.

```python
from nobelagentic import tool

@tool
def search_orders(customer_id: str, status: str = "open", limit: int = 10) -> list[dict]:
    """Find a customer's orders.

    Args:
        customer_id: The customer's ID.
        status: open, shipped or cancelled.
        limit: Max rows to return.
    """
    ...
```

Async functions work the same way. Return anything JSON-serialisable; it's stringified for the model.

TypeScript uses a `zod` schema, which is the documentation the model sees:

```ts
import { tool, z } from "nobelagentic";

const searchOrders = tool({
  name: "search_orders",
  description: "Find a customer's orders",
  parameters: z.object({
    customer_id: z.string(),
    status: z.enum(["open", "shipped", "cancelled"]).default("open"),
    limit: z.number().int().default(10),
  }),
  execute: async ({ customer_id, status, limit }) => { /* ... */ },
});
```

## Errors

A tool that throws does not crash the run. The error text goes back to the model as the tool result, so it can retry, pick another tool, or explain. The same happens for an unknown tool name or bad arguments.

## Built-in packs

Load a pack by name: `tools=["web", "files"]`. Packs are lazy — nothing is imported until you ask.

| Pack | Tools | Notes |
|---|---|---|
| `web` | `web_search`, `fetch_url`, `http_request` | No API key needed |
| `files` | `read_file`, `write_file`, `append_file`, `list_dir`, `search_files`, `delete_file` | Sandboxed to `NOBELAGENTIC_FILES_ROOT` (default: cwd) |
| `shell` | `run_command`, `run_python` / `run_javascript` | Opt-in only. Never loaded by default. |
| `time` | `now`, `date_add`, `convert_timezone` | IANA timezones |
| `math` | `calculate`, `convert_units` | Safe expression evaluation |
| `data` | `parse_json`, `json_query`, `csv_to_json`, `json_to_csv`, `summarize_table` | |

`nobelagentic tools list` prints every tool with its description.

## Credentials

A tool can declare the env vars it needs. Loading it without them fails immediately with a message naming the variable, rather than failing mid-run.

```python
@tool(requires=["STRIPE_KEY"])
def refund(charge_id: str) -> str: ...
```
