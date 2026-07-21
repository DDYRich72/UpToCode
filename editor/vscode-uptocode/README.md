# UpToCode for VS Code

This thin extension runs `uptocode scan` for a Python file on save and maps valid JSON
reports to editor diagnostics. It does not run repository scans, start a daemon, provide
code actions, or modify source.

Settings:

- `uptocode.executable` (default `uptocode`)
- `uptocode.extraArgs` (default `[]`; output-control flags are reserved)
- `uptocode.failOn` (`off`, `critical`, `warning`, or `info`; default `off`)

For a local package, run `npm ci && npm run verify`, then install the generated artifact:

```text
code --install-extension uptocode-vscode.vsix
```

Marketplace publication is operator-only and requires a publisher identity and listing.
