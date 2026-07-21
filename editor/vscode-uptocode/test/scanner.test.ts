import { execFile } from "node:child_process";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("node:child_process", () => ({ execFile: vi.fn() }));

import { buildArgs, GenerationGate, scanFile } from "../src/scanner.js";

const mockedExecFile = vi.mocked(execFile);

type ProcessError = Error & { code?: string | number };

function complete(error: ProcessError | null, stdout: string, stderr = ""): void {
  const callback = mockedExecFile.mock.calls.at(-1)?.[3];
  if (typeof callback !== "function") throw new Error("missing callback");
  callback(error, stdout, stderr);
}

describe("scanner", () => {
  beforeEach(() => mockedExecFile.mockReset());

  it("constructs shell-free arguments and reserves output controls", () => {
    expect(buildArgs("C:\\repo space\\agent.py", ["--rules", "AA014"], "warning")).toEqual([
      "scan", "C:\\repo space\\agent.py", "--rules", "AA014", "--format", "json", "--fail-on", "warning",
    ]);
    for (const flag of ["--format", "--output=x", "--fail-on"]) {
      expect(() => buildArgs("agent.py", [flag], "off")).toThrow(/reserved/);
    }
  });

  it.each([0, 1])("parses report exit %s", async (code) => {
    mockedExecFile.mockImplementationOnce(() => undefined as never);
    const pending = scanFile("uptocode", "agent.py", "C:\\repo", [], "off");
    const error = code === 0 ? null : Object.assign(new Error("threshold"), { code });
    complete(error, '{"findings":[],"analysis_warnings":[]}');
    expect((await pending).report?.findings).toEqual([]);
  });

  it("reports exit 2, spawn failure, and malformed JSON", async () => {
    mockedExecFile.mockImplementationOnce(() => undefined as never);
    const exitTwo = scanFile("uptocode", "agent.py", ".", [], "off");
    complete(Object.assign(new Error("usage"), { code: 2 }), "");
    expect((await exitTwo).error).toMatch(/scan failed/);

    mockedExecFile.mockImplementationOnce(() => undefined as never);
    const missing = scanFile("missing-uptocode", "agent.py", ".", [], "off");
    complete(Object.assign(new Error("ENOENT"), { code: "ENOENT" }), "");
    expect((await missing).error).toMatch(/ENOENT/);

    mockedExecFile.mockImplementationOnce(() => undefined as never);
    const malformed = scanFile("uptocode", "agent.py", ".", [], "off");
    complete(null, "not-json");
    expect((await malformed).error).toMatch(/malformed JSON/);
  });

  it("prevents an older save from replacing a newer generation", () => {
    const gate = new GenerationGate();
    const first = gate.next("file");
    const second = gate.next("file");
    expect(gate.isCurrent("file", first)).toBe(false);
    expect(gate.isCurrent("file", second)).toBe(true);
    gate.close("file");
    expect(gate.isCurrent("file", second)).toBe(false);
  });
});
