---
title: CLI
nav: CLI
order: 6
---
# CLI

Both packages ship the same command.

```bash
swarmagents run "What is 15% of 240?"
swarmagents run "Summarize this repo" --tools files,shell --model gpt-5
swarmagents chat --tools web,files --mcp github
swarmagents tools list
swarmagents mcp list
swarmagents mcp add <name> "<command or url>"
```

`run` executes one prompt and exits. `chat` keeps a conversation going for the session.

The default tool set is `web,time,math,data` — the packs that can't touch your disk or shell. Add `files` or `shell` explicitly.

In TypeScript, `npx swarmagents ...` works without a global install.
