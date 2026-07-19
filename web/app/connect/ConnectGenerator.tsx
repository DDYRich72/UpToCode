"use client";

import { useMemo, useState } from "react";

type Mode = "hosted" | "local";

export function ConnectGenerator() {
  const [mode, setMode] = useState<Mode>("hosted");
  const [endpoint, setEndpoint] = useState("https://mcp.archagent.example/mcp");
  const [root, setRoot] = useState("/absolute/path/to/repository");
  const [copied, setCopied] = useState(false);

  const config = useMemo(() => {
    if (mode === "local") {
      return `[mcp_servers.archagent]\ncommand = "uvx"\nargs = ["archagent-audit", "serve", "--transport", "stdio", "--root", "${root.replaceAll('"', '\\"')}"]\nrequired = true\nstartup_timeout_sec = 20\ntool_timeout_sec = 240`;
    }
    return `[mcp_servers.archagent]\nurl = "${endpoint.replaceAll('"', '\\"')}"\nbearer_token_env_var = "ARCHAGENT_API_KEY"\nrequired = true\nstartup_timeout_sec = 20\ntool_timeout_sec = 240`;
  }, [endpoint, mode, root]);

  async function copyConfig() {
    await navigator.clipboard.writeText(config);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div className="generator">
      <div className="tabs" role="tablist" aria-label="Connection mode">
        <button type="button" role="tab" aria-selected={mode === "hosted"} onClick={() => setMode("hosted")}>Hosted MCP</button>
        <button type="button" role="tab" aria-selected={mode === "local"} onClick={() => setMode("local")}>Local stdio</button>
      </div>

      {mode === "hosted" ? (
        <div className="field">
          <label htmlFor="endpoint">Hosted MCP endpoint</label>
          <input id="endpoint" value={endpoint} onChange={(event) => setEndpoint(event.target.value)} spellCheck={false} />
          <p className="hint">Set your issued key in the <code>ARCHAGENT_API_KEY</code> environment variable. It is not placed in the config file.</p>
        </div>
      ) : (
        <div className="field">
          <label htmlFor="root">Allowed repository root</label>
          <input id="root" value={root} onChange={(event) => setRoot(event.target.value)} spellCheck={false} />
          <p className="hint">ArchAgent resolves and enforces this boundary before any local path tool reads a file.</p>
        </div>
      )}

      <div className="codeBlock">
        <pre aria-label="Generated Codex MCP configuration"><code>{config}</code></pre>
        <button className="copyButton" type="button" onClick={copyConfig}>{copied ? "Copied" : "Copy Codex config"}</button>
      </div>
    </div>
  );
}
