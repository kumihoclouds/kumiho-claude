---
description: Set up Kumiho authentication for memory tools
argument-hint: "[token]"
---

# Kumiho Auth Setup

Authenticate the kumiho-memory plugin. There are **two** authentication
methods — choose whichever fits the user's workflow.

## Steps

1. Ask the user which method they'd like to use (skip if they already provided
   a token as an argument — that implies Method A):

   - **A - Dashboard API token**: Long-lived token minted from the kumiho.io dashboard. No interactive login needed.
   - **B - CLI login**: Email + password sign-in via `kumiho-cli login`. Creates a session token locally.

### Method A — Dashboard API token

1. If no token argument was provided, ask the user to paste their
   **Kumiho API token** (a JWT from the dashboard). Remind them:
   - The token looks like `eyJ...` (three dot-separated parts).
   - They can get it from the Kumiho Cloud dashboard under **API Tokens**.
   - Both raw JWT and `Bearer <jwt>` formats are accepted.

2. Run the caching script via Bash, passing the token through stdin to avoid
   shell history exposure:
   ```text
   echo '<token>' | python "${CLAUDE_PLUGIN_ROOT}/scripts/cache_auth_token.py" --stdin
   ```
   If `CLAUDE_PLUGIN_ROOT` is not set, use the path relative to the plugin
   directory (e.g., `./kumiho-cowork/scripts/cache_auth_token.py`).

3. If the script exits 0, confirm success:
   - "API token cached under `~/.kumiho/kumiho_authentication.json` (as
     `api_token` — your login session tokens are not affected)."
   - "It will be picked up on the next MCP server restart. You can restart
     the session now, or continue — memory tools will activate in your next
     session."

4. If the script exits non-zero, relay the error message and ask the user to
   double-check their token.

### Method B — CLI login

1. Tell the user to run `kumiho-cli login` in their terminal:
   ```text
   kumiho-cli login
   ```
   This will prompt for their email and password and create
   `~/.kumiho/kumiho_authentication.json` with `id_token` and
   `control_plane_token`.

2. Let them know:
   - "Once the login completes, restart this session (or start a new one) and
     memory tools will authenticate automatically."
   - "Session tokens expire — you may need to re-run `kumiho-cli login`
     periodically."

## Guardrails

- Do not log or echo the full token in any output shown to the user.
- If the user provides the token as a command argument, still prefer piping
  through stdin for security.
- Never overwrite session tokens (`id_token`, `control_plane_token`) when
  caching a dashboard API token — the script stores them under separate keys.
