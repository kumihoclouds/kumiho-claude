# Connectors

This plugin uses one local MCP server:

- `kumiho-memory` (stdio)
  - command: `python ${CLAUDE_PLUGIN_ROOT}/scripts/run_kumiho_mcp.py`
  - bootstrap: creates a venv and installs `kumiho[mcp]` + `kumiho-memory[all]`

## Required environment

- `KUMIHO_AUTH_TOKEN` (JWT bearer token)
  - set this in Claude session env (for example `.claude/settings.local.json`)

## Optional environment

- `KUMIHO_CONTROL_PLANE_URL` (default: `https://control.kumiho.cloud`)
- `KUMIHO_MCP_LOG_LEVEL` (default: `INFO`)
- `KUMIHO_COWORK_HOME` (override runtime directory)
- `KUMIHO_COWORK_PACKAGE_SPEC` (override package install spec)
- `KUMIHO_COWORK_DISABLE_LLM_FALLBACK` (disable local no-key LLM fallback mode)

`KUMIHO_SERVER_ENDPOINT` and `KUMIHO_SERVER_ADDRESS` are intentionally ignored by
the launcher to enforce control-plane discovery routing.

## Verify connection

1. Install and enable plugin.
2. Start a session.
3. Confirm Kumiho tools appear, for example:
   - `kumiho_chat_add`
   - `kumiho_chat_get`
   - `kumiho_chat_clear`
   - `kumiho_memory_ingest`
   - `kumiho_memory_recall`
   - `kumiho_memory_consolidate`
   - `kumiho_memory_dream_state`

If memory calls fail with `invalid_id_token`, refresh `KUMIHO_AUTH_TOKEN`
and verify `/api/memory/redis` is deployed with control-plane token verification.

If direct memory-store calls fail with `StatusCode.UNAVAILABLE` to
`127.0.0.1:8080`, discovery did not resolve cloud routing. Ensure
`/api/discovery/tenant` is deployed with control-plane token verification.
