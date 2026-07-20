"use client";

import { type KeyboardEvent, useMemo, useState } from "react";

type Mode = "hosted" | "local";
const HOSTED_ENDPOINT = "https://uptocode-mcp-1015314816960.us-central1.run.app/mcp";

export function ConnectGenerator() {
  const [mode, setMode] = useState<Mode>("local");
  const [endpoint, setEndpoint] = useState(HOSTED_ENDPOINT);
  const [root, setRoot] = useState("/absolute/path/to/repository");
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");

  const config = useMemo(() => {
    if (mode === "local") {
      return `[mcp_servers.uptocode]\ncommand = "uvx"\nargs = ["uptocode", "serve", "--transport", "stdio", "--root", "${root.replaceAll('"', '\\"')}"]\nrequired = true\nstartup_timeout_sec = 20\ntool_timeout_sec = 240`;
    }
    const hostedUrl = endpoint.trim() || HOSTED_ENDPOINT;
    return `[mcp_servers.uptocode]\nurl = "${hostedUrl.replaceAll('"', '\\"')}"\nbearer_token_env_var = "UPTOCODE_API_KEY"\nrequired = true\nstartup_timeout_sec = 20\ntool_timeout_sec = 240`;
  }, [endpoint, mode, root]);

  async function copyConfig() {
    try {
      await navigator.clipboard.writeText(config);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
    window.setTimeout(() => setCopyStatus("idle"), 1800);
  }

  function handleTabKey(event: KeyboardEvent<HTMLButtonElement>) {
    const order: Mode[] = ["local", "hosted"];
    const current = order.indexOf(mode);
    let next = current;

    if (event.key === "ArrowRight") next = (current + 1) % order.length;
    if (event.key === "ArrowLeft") next = (current - 1 + order.length) % order.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = order.length - 1;
    if (next === current) return;

    event.preventDefault();
    const nextMode = order[next];
    setMode(nextMode);
    document.getElementById(`${nextMode}-tab`)?.focus();
  }

  return (
    <div className="generator">
      <div className="tabs" role="tablist" aria-label="Connection mode">
        <button id="local-tab" type="button" role="tab" aria-selected={mode === "local"} aria-controls="local-panel" tabIndex={mode === "local" ? 0 : -1} onClick={() => setMode("local")} onKeyDown={handleTabKey}>Local stdio</button>
        <button id="hosted-tab" type="button" role="tab" aria-selected={mode === "hosted"} aria-controls="hosted-panel" tabIndex={mode === "hosted" ? 0 : -1} onClick={() => setMode("hosted")} onKeyDown={handleTabKey}>Hosted MCP</button>
      </div>

      {mode === "hosted" ? (
        <div id="hosted-panel" className="field" role="tabpanel" aria-labelledby="hosted-tab">
          <label htmlFor="endpoint">Hosted MCP endpoint</label>
          <input id="endpoint" type="url" value={endpoint} onChange={(event) => setEndpoint(event.target.value)} spellCheck={false} />
          <p className="hint">The verified production endpoint is prefilled. Set its separately issued key in <code>UPTOCODE_API_KEY</code>; this page never receives it.</p>
        </div>
      ) : (
        <div id="local-panel" className="field" role="tabpanel" aria-labelledby="local-tab">
          <label htmlFor="root">Allowed repository root</label>
          <input id="root" value={root} onChange={(event) => setRoot(event.target.value)} spellCheck={false} />
          <p className="hint">UpToCode resolves and enforces this boundary before any local path tool reads a file.</p>
        </div>
      )}

      <div className="codeBlock">
        <pre aria-label="Generated Codex MCP configuration"><code>{config}</code></pre>
        <button className="copyButton" type="button" onClick={copyConfig}>{copyStatus === "copied" ? "Copied" : "Copy Codex config"}</button>
        <span className="copyStatus" role="status" aria-live="polite">{copyStatus === "failed" ? "Copy failed. Select the configuration text and copy it manually." : ""}</span>
      </div>
    </div>
  );
}
