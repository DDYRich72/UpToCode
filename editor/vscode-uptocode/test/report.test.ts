import { describe, expect, it } from "vitest";

import { mapFindings, parseReport } from "../src/report.js";

describe("report mapping", () => {
  it("maps severity, citation, full-line coordinate, evidence, and maturity", () => {
    const report = parseReport(JSON.stringify({
      findings: [{
        rule_id: "AA017", severity: "warning", title: "Tool error", file: "agent.py",
        line: 7, maturity: "experimental", citations: [{ url: "https://example.test/rule" }],
        verdict: { observed: "One generic response." },
      }],
      analysis_warnings: [],
    }));
    expect(mapFindings(report)).toEqual([{
      line: 7,
      severity: "warning",
      code: "AA017",
      href: "https://example.test/rule",
      message: "Tool error [experimental] — One generic response.",
    }]);
  });

  it("rejects malformed reports", () => {
    expect(() => parseReport("{}" )).toThrow(/missing findings/);
    expect(() => parseReport("not json")).toThrow();
  });
});
