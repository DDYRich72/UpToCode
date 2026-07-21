import { describe, expect, it } from "vitest";

import { toDiagnosticUpdate } from "../src/updates.js";

describe("diagnostic updates", () => {
  it("clears diagnostics for valid clean scans and renders warnings with location", () => {
    const update = toDiagnosticUpdate({
      stderr: "",
      report: {
        findings: [],
        analysis_warnings: [{ code: "DYNAMIC", message: "Needs review", file: "agent.py", line: 9 }],
      },
    });
    expect(update.diagnostics).toEqual([]);
    expect(update.messages).toEqual(["agent.py:9: DYNAMIC: Needs review"]);
  });

  it("clears stale diagnostics and explains scanner failures", () => {
    expect(toDiagnosticUpdate({ stderr: "not found", error: "scan failed" })).toEqual({
      diagnostics: [],
      messages: ["scan failed", "not found"],
    });
  });
});
