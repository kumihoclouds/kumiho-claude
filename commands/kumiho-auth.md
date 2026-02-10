---
description: Set up Kumiho authentication for memory tools
argument-hint: "[token]"
---

# Kumiho Auth Setup

Authenticate the kumiho-memory plugin so that memory tools can connect to
the Kumiho Cloud backend.

## Steps

### 1. Choose authentication method

If the user already provided a token as the command argument (`$ARGUMENTS`),
skip straight to **Method A -- step 2** (cache the token).

Otherwise, use the `AskUserQuestion` tool to ask the user which method they
prefer. Present exactly these two options:

- **A -- Dashboard API token**: Paste a long-lived JWT from the Kumiho Cloud
  dashboard. No interactive login needed.
- **B -- CLI login**: Sign in with email and password via `kumiho-cli login`.

### 2. Execute the chosen method

#### Method A -- Dashboard API token

1. If no token was provided as an argument, ask the user to paste their
   **Kumiho API token** using the `AskUserQuestion` tool. Remind them:
   - The token looks like `eyJ...` (three dot-separated base64url parts).
   - They can find it in the Kumiho Cloud dashboard under **API Tokens**.
   - Both raw JWT and `Bearer <jwt>` formats are accepted.

2. Extract the token string. Strip any surrounding quotes, whitespace,
   or a leading `Bearer` prefix before passing it to the cache script.

3. Store the token by running this Bash command. Replace `<CLEANED_TOKEN>`
   with the extracted JWT -- **do not** echo it back in visible output:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/cache_auth_token.py" --token "<CLEANED_TOKEN>"
   ```

   If `CLAUDE_PLUGIN_ROOT` is not set, fall back to a path relative to
   the plugin directory:

   ```bash
   python "<plugin-dir>/scripts/cache_auth_token.py" --token "<CLEANED_TOKEN>"
   ```

4. **On success (exit 0)**, tell the user:
   - "API token cached at `~/.kumiho/kumiho_authentication.json` (stored
     under `api_token` -- any CLI login session tokens are not affected)."
   - "The MCP server will pick this up on the next session restart.
     You can restart now, or continue -- memory tools will activate in
     your next session."

5. **On failure (non-zero exit)**, relay the error and ask the user to
   double-check their token.

#### Method B -- CLI login

1. Tell the user to run the following in their own terminal (outside Claude):

   ```bash
   kumiho-cli login
   ```

   This will prompt for email and password and create
   `~/.kumiho/kumiho_authentication.json` with `id_token` and
   `control_plane_token`.

2. Let them know:
   - "Once login completes, restart this session (or start a new one)
     and memory tools will authenticate automatically."
   - "Session tokens expire -- you may need to re-run `kumiho-cli login`
     periodically."

## Guardrails

- **Never** log or echo the full token in user-visible output.
- If the user provides the token as a command argument, still prefer
  passing it via `--token` rather than piping through stdin, to avoid
  shell-quoting issues on Windows.
- Never overwrite session tokens (`id_token`, `control_plane_token`)
  when caching a dashboard API token -- the script handles this
  automatically by storing under a separate `api_token` key.
