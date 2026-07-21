import * as vscode from "vscode";
import {
  LanguageClient,
  type LanguageClientOptions,
  type ServerOptions,
} from "vscode-languageclient/node";

import {
  buildSuppressionText,
  findFixplanFingerprintOffset,
  findSafeInsertionLine,
  formatLocalDate,
  validateExpiry,
  validateOwner,
  validateReason,
  type SuppressionPayload,
} from "./actions.js";

let client: LanguageClient | undefined;

async function suppressWithMetadata(payload: SuppressionPayload): Promise<void> {
  const document = await vscode.workspace.openTextDocument(vscode.Uri.parse(payload.uri));
  if (vscode.window.activeTextEditor?.document.uri.toString() !== document.uri.toString()) {
    void vscode.window.showErrorMessage("Open the finding document before applying its suppression.");
    return;
  }
  if (document.version !== payload.version) {
    void vscode.window.showErrorMessage("The document changed; request the suppression action again.");
    return;
  }
  const owner = await vscode.window.showInputBox({
    title: `Suppress ${payload.ruleId}`,
    prompt: "Owner (letters, numbers, ., _, @, and -)",
    validateInput: validateOwner,
  });
  if (owner === undefined) return;
  const reason = await vscode.window.showInputBox({
    title: `Suppress ${payload.ruleId}`,
    prompt: "Reason",
    validateInput: validateReason,
  });
  if (reason === undefined) return;
  const defaultExpiry = new Date();
  defaultExpiry.setDate(defaultExpiry.getDate() + 30);
  const expires = await vscode.window.showInputBox({
    title: `Suppress ${payload.ruleId}`,
    prompt: "Expiry (YYYY-MM-DD)",
    value: formatLocalDate(defaultExpiry),
    validateInput: (value) => validateExpiry(value, new Date()),
  });
  if (expires === undefined) return;
  const confirmation = await vscode.window.showWarningMessage(
    `Insert a suppression for ${payload.ruleId} in the active document?`,
    { modal: true },
    "Apply",
  );
  if (confirmation !== "Apply") return;
  if (
    vscode.window.activeTextEditor?.document.uri.toString() !== document.uri.toString()
    || document.version !== payload.version
  ) {
    void vscode.window.showErrorMessage("The active document changed; request the action again.");
    return;
  }

  const lines = document.getText().split(/\r?\n/);
  const insertionLine = findSafeInsertionLine(lines, payload.line, document.languageId);
  const indentation = document.lineAt(insertionLine).text.match(/^\s*/)?.[0] ?? "";
  const eol = document.eol === vscode.EndOfLine.CRLF ? "\r\n" : "\n";
  const edit = new vscode.WorkspaceEdit();
  edit.insert(
    document.uri,
    new vscode.Position(insertionLine, 0),
    `${indentation}${buildSuppressionText(document.languageId, payload.ruleId, owner, reason, expires)}${eol}`,
  );
  if (!(await vscode.workspace.applyEdit(edit))) {
    void vscode.window.showErrorMessage("VS Code could not apply the suppression edit.");
  }
}

async function openFixplan(payload: { uri: string; fingerprint: string }): Promise<void> {
  const document = await vscode.workspace.openTextDocument(vscode.Uri.parse(payload.uri));
  const offset = findFixplanFingerprintOffset(document.getText(), payload.fingerprint);
  if (offset < 0) {
    void vscode.window.showErrorMessage("The FIXPLAN entry is no longer present.");
    return;
  }
  const editor = await vscode.window.showTextDocument(document);
  const position = document.positionAt(offset);
  editor.selection = new vscode.Selection(position, position);
  editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenter);
}

export function activate(context: vscode.ExtensionContext): void {
  const executable = vscode.workspace.getConfiguration("uptocode").get<string>("executable", "uptocode");
  const serverOptions: ServerOptions = { command: executable, args: ["lsp"] };
  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { scheme: "file", language: "python" },
      { scheme: "file", language: "typescript" },
      { scheme: "file", language: "typescriptreact" },
    ],
    outputChannelName: "UpToCode",
  };
  client = new LanguageClient("uptocode", "UpToCode", serverOptions, clientOptions);

  context.subscriptions.push(
    client,
    vscode.commands.registerCommand("uptocode.suppressWithMetadata", suppressWithMetadata),
    vscode.commands.registerCommand("uptocode.openCitation", (url: string) =>
      vscode.env.openExternal(vscode.Uri.parse(url)),
    ),
    vscode.commands.registerCommand("uptocode.openFixplan", openFixplan),
    vscode.commands.registerCommand("uptocode.scanFile", () => {
      const document = vscode.window.activeTextEditor?.document;
      if (document?.uri.scheme === "file") {
        void client?.sendNotification("textDocument/didSave", {
          textDocument: { uri: document.uri.toString() },
        });
      }
    }),
  );
  void client.start();
}

export async function deactivate(): Promise<void> {
  await client?.stop();
}
