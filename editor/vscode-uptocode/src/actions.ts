export interface SuppressionPayload {
  uri: string;
  version: number;
  line: number;
  ruleId: string;
  fingerprint: string;
}

const OWNER = /^[A-Za-z0-9_.@-]+$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function formatLocalDate(value: Date): string {
  return [
    value.getFullYear().toString().padStart(4, "0"),
    (value.getMonth() + 1).toString().padStart(2, "0"),
    value.getDate().toString().padStart(2, "0"),
  ].join("-");
}

export function validateOwner(value: string): string | undefined {
  return OWNER.test(value) ? undefined : "Enter a non-empty owner using letters, numbers, ., _, @, or -.";
}

export function validateReason(value: string): string | undefined {
  if (!value.trim()) return "Enter a reason.";
  return /["\r\n]/.test(value) ? "Reason cannot contain quotes or line breaks." : undefined;
}

export function validateExpiry(value: string, today: Date): string | undefined {
  if (!DATE.test(value)) return "Use YYYY-MM-DD.";
  const parts = value.split("-");
  const year = Number(parts[0]);
  const month = Number(parts[1]);
  const day = Number(parts[2]);
  const parsed = new Date(year, month - 1, day);
  if (
    Number.isNaN(parsed.valueOf())
    || parsed.getFullYear() !== year
    || parsed.getMonth() !== month - 1
    || parsed.getDate() !== day
  ) {
    return "Enter a valid calendar date.";
  }
  const todayKey = formatLocalDate(today);
  return value < todayKey ? "Expiry cannot be in the past." : undefined;
}

export function buildSuppressionText(
  languageId: string,
  ruleId: string,
  owner: string,
  reason: string,
  expires: string,
): string {
  const marker = languageId === "python" ? "#" : "//";
  return `${marker} uptocode: ignore ${ruleId} owner=${owner} reason="${reason}" expires=${expires}`;
}

export function findFixplanFingerprintOffset(content: string, fingerprint: string): number {
  const marker = `Fingerprint: \`${fingerprint}\``;
  let offset = 0;
  for (const line of content.split(/(?<=\n)/)) {
    if (line.replace(/\r?\n$/, "") === marker) return offset + line.indexOf(fingerprint);
    offset += line.length;
  }
  return -1;
}

export function findSafeInsertionLine(
  lines: readonly string[],
  diagnosticLine: number,
  languageId: string,
): number {
  let line = Math.max(0, Math.min(diagnosticLine, Math.max(0, lines.length - 1)));
  if (languageId === "python" || languageId === "typescript" || languageId === "typescriptreact") {
    while (line > 0 && lines[line - 1]?.trimStart().startsWith("@")) line -= 1;
    while (line > 0 && lines[line - 1]?.trimEnd().endsWith("\\")) line -= 1;
  }
  return line;
}
