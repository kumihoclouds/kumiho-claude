# Connectors

This plugin uses one local MCP server:

- `kumiho-memory` (stdio)
  - command: `python ${CLAUDE_PLUGIN_ROOT}/scripts/run_kumiho_mcp.py`
  - bootstrap: creates a venv and installs `kumiho[mcp]` + `kumiho-memory[all]`

## Required environment

- `KUMIHO_AUTH_TOKEN` (JWT bearer token) or `KUMIHO_AUTH_TOKEN_FILE`

## Optional environment

- `KUMIHO_CONTROL_PLANE_URL` (default: `https://control.kumiho.cloud`)
- `KUMIHO_MCP_LOG_LEVEL` (default: `INFO`)
- `KUMIHO_COWORK_HOME` (override runtime directory)
- `KUMIHO_COWORK_PACKAGE_SPEC` (override package install spec)
- `KUMIHO_COWORK_DISABLE_LLM_FALLBACK` (disable local no-key LLM fallback mode)

## Verify connection

1. Install and enable plugin.
2. Start a session.
3. Confirm Kumiho tools appear, for example:
   - `kumiho_memory_ingest`
   - `kumiho_memory_recall`
   - `kumiho_memory_consolidate`
