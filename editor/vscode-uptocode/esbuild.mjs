import * as esbuild from "esbuild";
import { rm } from "node:fs/promises";

await rm("dist/uptocode-vscode.vsix", { force: true });

await esbuild.build({
  entryPoints: ["src/extension.ts"],
  outfile: "dist/extension.js",
  bundle: true,
  external: ["vscode"],
  format: "cjs",
  platform: "node",
  target: "node22",
  sourcemap: true,
});
