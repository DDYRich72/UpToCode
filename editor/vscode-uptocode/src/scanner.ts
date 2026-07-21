import { execFile } from "node:child_process";

import { parseReport, type Report } from "./report.js";

export type FailOn = "off" | "critical" | "warning" | "info";

const RESERVED = ["--format", "--output", "--fail-on"];

export function buildArgs(file: string, extraArgs: readonly string[], failOn: FailOn): string[] {
  const reserved = extraArgs.find((argument) =>
    RESERVED.some((flag) => argument === flag || argument.startsWith(`${flag}=`)),
  );
  if (reserved) throw new Error(`${reserved} is reserved by the UpToCode extension`);
  const args = ["scan", file, ...extraArgs, "--format", "json"];
  if (failOn !== "off") args.push("--fail-on", failOn);
  return args;
}

export interface ScanOutcome {
  report?: Report;
  error?: string;
  stderr: string;
}

export function scanFile(
  executable: string,
  file: string,
  cwd: string,
  extraArgs: readonly string[],
  failOn: FailOn,
): Promise<ScanOutcome> {
  let args: string[];
  try {
    args = buildArgs(file, extraArgs, failOn);
  } catch (error) {
    return Promise.resolve({ error: String(error), stderr: "" });
  }
  return new Promise((resolve) => {
    execFile(executable, args, { cwd, windowsHide: true }, (error, stdout, stderr) => {
      const exitCode = typeof error?.code === "number" ? error.code : error ? 2 : 0;
      if (exitCode !== 0 && exitCode !== 1) {
        resolve({ error: `scan failed (${error?.message ?? `exit ${exitCode}`})`, stderr });
        return;
      }
      try {
        resolve({ report: parseReport(stdout), stderr });
      } catch (parseError) {
        resolve({ error: `scan returned malformed JSON: ${String(parseError)}`, stderr });
      }
    });
  });
}

export class GenerationGate {
  private readonly generations = new Map<string, number>();

  next(key: string): number {
    const generation = (this.generations.get(key) ?? 0) + 1;
    this.generations.set(key, generation);
    return generation;
  }

  isCurrent(key: string, generation: number): boolean {
    return this.generations.get(key) === generation;
  }

  close(key: string): void {
    this.generations.delete(key);
  }
}
