import type { Metadata } from "next";
import Link from "next/link";
import { ConnectGenerator } from "./ConnectGenerator";

export const metadata: Metadata = {
  title: "Connect UpToCode MCP",
  description: "Generate a local or hosted UpToCode MCP configuration without sending your key to this site.",
};

export default function ConnectPage() {
  return (
    <main id="main-content">
      <nav className="nav" aria-label="Connection navigation">
        <Link className="brand" href="/">UpToCode</Link>
        <Link className="textLink" href="/">Back to overview</Link>
      </nav>
      <section className="connectShell">
        <div className="connectIntro">
          <p className="eyebrow">Connection setup</p>
          <h1>Choose where your code is analyzed.</h1>
          <p className="lede">Local mode reads a bounded workspace on your machine. The verified hosted endpoint analyzes only content explicitly sent through an MCP tool call.</p>
        </div>
        <ConnectGenerator />
        <div className="callout">
          UpToCode publishes its verified hosted address,{" "}
          <code>https://uptocode-mcp-1015314816960.us-central1.run.app/mcp</code>, but never
          collects a credential. Codex reads the separately issued key from your local{" "}
          <code>UPTOCODE_API_KEY</code> environment variable.
        </div>
        <section className="connectionChecks" aria-labelledby="verify-connection">
          <h2 id="verify-connection">Verify the connection</h2>
          <ol>
            <li>Save the generated block in <code>~/.codex/config.toml</code>.</li>
            <li>Restart Codex, then confirm the UpToCode server and its rule tools are listed.</li>
            <li>Run <code>check_loop</code> with synthetic code before submitting project source.</li>
          </ol>
          <p>Hosted readiness is available at the service&apos;s <code>/readyz</code> path. A ready endpoint returns its UpToCode version without requiring or accepting source code.</p>
        </section>
      </section>
    </main>
  );
}
