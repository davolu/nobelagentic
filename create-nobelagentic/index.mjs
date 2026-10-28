#!/usr/bin/env node
// Scaffold a NobelAgentic agent project:  npm create nobelagentic my-agent
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const name = process.argv[2];
if (!name || name.startsWith("-")) {
  console.error("usage: npm create nobelagentic <project-name>");
  process.exit(1);
}
if (existsSync(name)) {
  console.error(`error: '${name}' already exists`);
  process.exit(1);
}

const files = {
  "package.json": JSON.stringify(
    {
      name,
      private: true,
      type: "module",
      scripts: { dev: "tsx src/agent.ts" },
      dependencies: {
        nobelagentic: "^0.1.0",
        "@anthropic-ai/sdk": "^0.50.0",
      },
      devDependencies: {
        tsx: "^4.19.0",
        typescript: "^5.6.0",
        "@types/node": "^22.0.0",
      },
    },
    null,
    2
  ) + "\n",

  "tsconfig.json": JSON.stringify(
    {
      compilerOptions: {
        module: "esnext",
        target: "es2022",
        moduleResolution: "bundler",
        strict: true,
        skipLibCheck: true,
        noEmit: true,
      },
      include: ["src"],
    },
    null,
    2
  ) + "\n",

  "src/agent.ts": `import { Agent, tool, z } from "nobelagentic";

const lookupOrder = tool({
  name: "lookup_order",
  description: "Look up an order by ID (replace with your real data source)",
  parameters: z.object({ orderId: z.string() }),
  execute: ({ orderId }) => ({ orderId, status: "shipped", etaDays: 2 }),
});

const agent = new Agent("You are the support agent for ${name}. Be warm and brief.", {
  tools: [lookupOrder, "time", "math"],
});

console.log(String(await agent.run("Where is order 42?")));
`,

  ".gitignore": "node_modules/\n.env\n",

  "README.md": `# ${name}

An agent scaffolded with \`npm create nobelagentic\`.

\`\`\`bash
npm install
export ANTHROPIC_API_KEY=...   # or install 'openai' and set OPENAI_API_KEY
npm run dev
\`\`\`

Edit \`src/agent.ts\`: swap \`lookupOrder\` for a real tool, add packs (\`"web"\`, \`"files"\`)
or MCP servers (\`mcp: ["github"]\`). Docs: https://nobelagentic.vercel.app/docs
`,
};

mkdirSync(join(name, "src"), { recursive: true });
for (const [file, content] of Object.entries(files)) {
  writeFileSync(join(name, file), content);
}

console.log(`created ${name}/ (${Object.keys(files).join(", ")})`);
console.log(`\n  cd ${name}`);
console.log("  npm install");
console.log("  export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY");
console.log("  npm run dev");
