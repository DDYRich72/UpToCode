# UpToCode for VS Code

The extension starts the persistent `uptocode lsp` stdio server and publishes file-scoped
UpToCode diagnostics when supported Python or TypeScript documents are opened or saved.
It does not index the workspace, scan on every keystroke, invoke judgment, or auto-fix.

Diagnostic actions can:

- insert a structured suppression after owner/reason/expiry validation and explicit
  confirmation (the document is not saved automatically),
- open the rule's primary public citation, and
- open an exact-fingerprint entry in workspace-root `FIXPLAN.md`.

Set `uptocode.executable` when the `uptocode` command is not on VS Code's PATH. Scan policy
belongs in `.uptocode.yml`; the 0.1 subprocess settings `extraArgs` and `failOn` no longer
apply.

For a local package, run `npm ci && npm run verify`, then install the generated artifact:

```text
code --install-extension uptocode-vscode.vsix
```

Marketplace publication is operator-only and requires a publisher identity and listing.
