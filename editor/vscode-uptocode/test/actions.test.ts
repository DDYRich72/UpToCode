import { describe, expect, it } from "vitest";

import {
  buildSuppressionText,
  findFixplanFingerprintOffset,
  findSafeInsertionLine,
  formatLocalDate,
  validateExpiry,
  validateOwner,
  validateReason,
} from "../src/actions.js";

describe("suppression actions", () => {
  it("validates the parser-compatible metadata contract", () => {
    expect(validateOwner("team@example.com")).toBeUndefined();
    expect(validateOwner("bad owner")).toMatch(/owner/);
    expect(validateReason("accepted until migration")).toBeUndefined();
    expect(validateReason('bad "reason"')).toMatch(/quotes/);
    expect(validateExpiry("2026-08-20", new Date(2026, 6, 21))).toBeUndefined();
    expect(validateExpiry("2026-02-30", new Date(2026, 0, 1))).toMatch(/calendar/);
    expect(validateExpiry("2026-07-20", new Date(2026, 6, 21))).toMatch(/past/);
    expect(formatLocalDate(new Date(2026, 6, 21))).toBe("2026-07-21");
  });

  it("emits exact Python and TypeScript directives", () => {
    expect(buildSuppressionText("python", "AA001", "team", "bounded elsewhere", "2026-08-20"))
      .toBe('# uptocode: ignore AA001 owner=team reason="bounded elsewhere" expires=2026-08-20');
    expect(buildSuppressionText("typescript", "AA001", "team", "bounded elsewhere", "2026-08-20"))
      .toBe('// uptocode: ignore AA001 owner=team reason="bounded elsewhere" expires=2026-08-20');
  });

  it("inserts before decorators and explicit continuation chains", () => {
    expect(findSafeInsertionLine(["@first", "@second", "def run():"], 2, "python")).toBe(0);
    expect(findSafeInsertionLine(["value = \\", "    call()"], 1, "python")).toBe(0);
    expect(findSafeInsertionLine(["const value = 1;"], 0, "typescript")).toBe(0);
  });

  it("matches only an exact generated FIXPLAN fingerprint entry", () => {
    const fingerprint = "e529db308cff0c2d511ad646";
    expect(findFixplanFingerprintOffset(`Fingerprint: \`${fingerprint}\`\n`, fingerprint)).toBe(14);
    expect(findFixplanFingerprintOffset(`Fingerprint: \`${fingerprint}0\`\n`, fingerprint)).toBe(-1);
    expect(findFixplanFingerprintOffset(`note ${fingerprint}\n`, fingerprint)).toBe(-1);
  });
});
