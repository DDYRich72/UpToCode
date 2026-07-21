import Link from "next/link";

const rules = [
  "Execution bounds",
  "Run budgets",
  "Approval gates",
  "Tool validation",
  "Prompt boundaries",
  "Sensitive data",
  "Resilience",
  "Orchestration",
  "Tool schemas",
  "Output validation",
  "Agent evals",
  "Observability",
  "Context growth",
  "Network MCP auth",
  "Tool annotations",
  "Strict tool inputs",
  "Actionable tool errors",
  "Enforced prompt policies",
];

export default function Home() {
  return (
    <main id="main-content">
      <nav className="nav" aria-label="Primary navigation">
        <Link className="brand" href="/">UpToCode</Link>
        <div className="navLinks">
          <a href="#rules">Rules</a>
          <a href="#privacy">Privacy</a>
          <Link className="button small" href="/connect">Connect MCP</Link>
        </div>
      </nav>

      <section className="hero">
        <p className="eyebrow">Architecture evidence for Python agent systems</p>
        <h1>Find the failure mode before your agent finds it in production.</h1>
        <p className="lede">
          UpToCode audits execution bounds, budgets, approvals, validation,
          resilience, evals, and observability. Every finding includes source
          evidence, uncertainty, and an approval-driven remediation plan.
        </p>
        <div className="actions">
          <Link className="button" href="/connect">Connect the MCP</Link>
          <a className="textLink" href="#install">Install locally</a>
        </div>
      </section>

      <section className="proof" aria-label="Product guarantees">
        <article><strong>Audits itself</strong><span>Zero production findings, suppressions, or unexplained warnings.</span></article>
        <article><strong>Static first</strong><span>No network calls by default.</span></article>
        <article><strong>Fail closed</strong><span>Unsupported code is reported, never declared clean.</span></article>
        <article><strong>Non-mutating</strong><span>Review and planning never rewrite source.</span></article>
      </section>

      <section className="section split" id="install">
        <div>
          <p className="eyebrow">Two access modes</p>
          <h2>Keep repositories local. Use hosted checks when you choose.</h2>
        </div>
        <div className="modeGrid">
          <article className="card">
            <h3>Local stdio MCP</h3>
            <p>Full repository, file, diff, review, and FIXPLAN analysis inside an explicitly bounded workspace.</p>
            <code>uvx uptocode serve --root /path/to/repo</code>
          </article>
          <article className="card">
            <h3>Hosted MCP</h3>
            <p>Stateless source, diff, loop, schema, rule, review, and plan tools. No server filesystem access or code history.</p>
            <Link className="textLink" href="/connect">Generate connection config</Link>
          </article>
        </div>
      </section>

      <section className="section" id="rules">
        <p className="eyebrow">AA001—AA018</p>
        <h2>A production architecture contract, not a generic quality score.</h2>
        <div className="ruleGrid">
          {rules.map((rule, index) => (
            <article key={rule}>
              <span>AA{String(index + 1).padStart(3, "0")}</span>
              <strong>{rule}</strong>
            </article>
          ))}
        </div>
      </section>

      <section className="section split" id="privacy">
        <div>
          <p className="eyebrow">Trust boundary</p>
          <h2>Your code is untrusted input—even to us.</h2>
        </div>
        <div className="privacyCopy">
          <p>Local static scans stay offline. Hosted tools accept only code you explicitly submit and do not expose path-based repository tools.</p>
          <p>Optional model judgment requires separate code-sharing consent, uses bounded redacted excerpts, and cannot control trusted rule identity or severity.</p>
          <p>Hosted code, prompts, and reports are processed in request memory and are not retained.</p>
        </div>
      </section>

      <footer>
        <span>UpToCode 1.1 · Python 3.11+</span>
        <Link href="/connect">Connection instructions</Link>
      </footer>
    </main>
  );
}
