import assert from "node:assert/strict";
import test from "node:test";

async function render(pathname) {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${pathname}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${pathname}`, {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the functional UpToCode landing page", async () => {
  const response = await render("/");
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>UpToCode/);
  assert.match(html, /Find the failure mode before your agent finds it in production/);
  assert.match(html, /AA001/);
  assert.match(html, /AA013/);
  assert.match(html, /Local stdio MCP/);
  assert.match(html, /Hosted MCP/);
  assert.match(html, /href="\/connect"/);
  assert.match(html, /Audits itself/);
  assert.match(html, /id="main-content"/);
  assert.match(html, /Skip to main content/);
});

test("server-renders connection instructions without collecting a key", async () => {
  const response = await render("/connect");
  assert.equal(response.status, 200);

  const html = await response.text();
  assert.match(html, /Choose where your code is analyzed/);
  assert.match(html, /UPTOCODE_API_KEY/);
  assert.match(html, /command = &quot;uvx&quot;/);
  assert.match(html, /Local stdio/);
  assert.match(html, /verified hosted endpoint/i);
  assert.match(html, /aria-label="Connection navigation"/);
  assert.match(html, /https:\/\/uptocode-mcp-1015314816960\.us-central1\.run\.app\/mcp/);
  assert.match(html, /never collects a credential/i);
  assert.doesNotMatch(html, /type="password"|name="api[_-]?key"/i);
});
