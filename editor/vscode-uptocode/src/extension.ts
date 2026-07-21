import * as path from "node:path";
import * as vscode from "vscode";

import type { Severity } from "./report.js";
import { GenerationGate, scanFile, type FailOn } from "./scanner.js";
import { toDiagnosticUpdate } from "./updates.js";

const severityMap: Record<Severity, vscode.DiagnosticSeverity> = {
  critical: vscode.DiagnosticSeverity.Error,
  warning: vscode.DiagnosticSeverity.Warning,
  info: vscode.DiagnosticSeverity.Information,
};

export function activate(context: vscode.ExtensionContext): void {
  const diagnostics = vscode.languages.createDiagnosticCollection("uptocode");
  const output = vscode.window.createOutputChannel("UpToCode");
  const gate = new GenerationGate();

  const scan = async (document: vscode.TextDocument): Promise<void> => {
    if (document.languageId !== "python" || document.uri.scheme !== "file") return;
    const key = document.uri.toString();
    const generation = gate.next(key);
    const config = vscode.workspace.getConfiguration("uptocode", document.uri);
    const executable = config.get<string>("executable", "uptocode");
    const extraArgs = config.get<string[]>("extraArgs", []);
    const failOn = config.get<FailOn>("failOn", "off");
    const cwd = vscode.workspace.getWorkspaceFolder(document.uri)?.uri.fsPath
      ?? path.dirname(document.uri.fsPath);
    const outcome = await scanFile(executable, document.uri.fsPath, cwd, extraArgs, failOn);
    if (!gate.isCurrent(key, generation)) return;
    const update = toDiagnosticUpdate(outcome);
    if (!outcome.report) {
      diagnostics.delete(document.uri);
      for (const message of update.messages) output.appendLine(`${document.uri.fsPath}: ${message}`);
      return;
    }
    const mapped = update.diagnostics.map((item) => {
      const line = Math.min(item.line - 1, Math.max(0, document.lineCount - 1));
      const diagnostic = new vscode.Diagnostic(
        new vscode.Range(line, 0, line, document.lineAt(line).text.length),
        item.message,
        severityMap[item.severity],
      );
      diagnostic.source = "uptocode";
      diagnostic.code = item.href
        ? { value: item.code, target: vscode.Uri.parse(item.href) }
        : item.code;
      return diagnostic;
    });
    diagnostics.set(document.uri, mapped);
    for (const message of update.messages) output.appendLine(message);
  };

  context.subscriptions.push(
    diagnostics,
    output,
    vscode.workspace.onDidSaveTextDocument((document) => void scan(document)),
    vscode.workspace.onDidCloseTextDocument((document) => {
      gate.close(document.uri.toString());
      diagnostics.delete(document.uri);
    }),
    vscode.commands.registerCommand("uptocode.scanFile", () => {
      const document = vscode.window.activeTextEditor?.document;
      if (document) void scan(document);
    }),
  );
}

export function deactivate(): void {}
