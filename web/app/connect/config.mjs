const TOML_ESCAPES = {
  "\b": "\\b",
  "\t": "\\t",
  "\n": "\\n",
  "\f": "\\f",
  "\r": "\\r",
  '"': '\\"',
  "\\": "\\\\",
};

/**
 * Encode a JavaScript string as a TOML basic string.
 *
 * JSON and TOML share the common short escapes, while TOML additionally
 * requires every remaining C0 control character and DEL to be escaped.
 *
 * @param {string} value
 * @returns {string}
 */
export function tomlBasicString(value) {
  const encoded = value.replace(/[\u0000-\u001f\u007f"\\]/g, (character) => {
    const shortEscape = TOML_ESCAPES[character];
    if (shortEscape) return shortEscape;
    return `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`;
  });

  return `"${encoded}"`;
}

/** @param {string} root */
export function buildLocalConfig(root) {
  return `[mcp_servers.uptocode]\ncommand = "uvx"\nargs = ["uptocode", "serve", "--transport", "stdio", "--root", ${tomlBasicString(root)}]\nrequired = true\nstartup_timeout_sec = 20\ntool_timeout_sec = 240`;
}

/** @param {string} endpoint */
export function buildHostedConfig(endpoint) {
  return `[mcp_servers.uptocode]\nurl = ${tomlBasicString(endpoint)}\nbearer_token_env_var = "UPTOCODE_API_KEY"\nrequired = true\nstartup_timeout_sec = 20\ntool_timeout_sec = 240`;
}
