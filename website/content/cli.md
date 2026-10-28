---
title: CLI
nav: CLI
order: 6
---
# CLI

Both packages ship the same command.

```bash
nobelagentic run "What is 15% of 240?"
nobelagentic run "Summarize this repo" --tools files,shell --model gpt-5
nobelagentic chat --tools web,files --mcp github
nobelagentic tools list
nobelagentic mcp list
nobelagentic mcp add <name> "<command or url>"
```

`run` executes one prompt and exits. `chat` keeps a conversation going for the session.

The default tool set is `web,time,math,data` — the packs that can't touch your disk or shell. Add `files` or `shell` explicitly.

In TypeScript, `npx nobelagentic ...` works without a global install.
