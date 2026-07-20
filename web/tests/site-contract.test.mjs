import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function read(relativePath) {
  return readFile(new URL(relativePath, root), "utf8");
}

test("site package has no database or migration surface", async () => {
  const packageJson = JSON.parse(await read("package.json"));
  const serialized = JSON.stringify(packageJson);

  assert.doesNotMatch(serialized, /drizzle|database|migration/i);
  assert.deepEqual(JSON.parse(await read(".openai/hosting.json")), {});
  assert.doesNotMatch(await read("vite.config.ts"), /d1|r2|database|bucket/i);
  assert.doesNotMatch(await read("worker/index.ts"), /D1Database|\bDB\b/);
});

test("connection generator defaults local and uses the verified hosted endpoint", async () => {
  const source = await read("app/connect/ConnectGenerator.tsx");

  assert.match(source, /useState<Mode>\("local"\)/);
  assert.match(source, /https:\/\/uptocode-mcp-1015314816960\.us-central1\.run\.app\/mcp/);
  assert.doesNotMatch(source, /<HOSTED_MCP_URL>/);
  assert.match(source, /role="tabpanel"/);
  assert.match(source, /aria-controls=/);
  assert.match(source, /ArrowRight/);
  assert.doesNotMatch(source, /mcp\.uptocode\.example/);
});

test("site styles expose visible focus and reduced-motion behavior", async () => {
  const css = await read("app/globals.css");

  assert.match(css, /:focus-visible/);
  assert.match(css, /outline:\s*3px/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /scroll-behavior:\s*auto/);
});
