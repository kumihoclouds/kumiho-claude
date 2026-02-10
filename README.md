# Kumiho Cowork Plugin

Plugin for Claude that runs a local Kumiho MCP server with `kumiho-memory`.

## What works now

- Plugin manifest is valid for `claude plugin validate`.
- MCP server launches through a bootstrap script:
  - creates a dedicated virtualenv
  - installs/updates `kumiho[mcp]` and `kumiho-memory[all]`
  - runs `python -m kumiho.mcp_server`
- Memory tools from `kumiho-memory` are auto-discovered by Kumiho MCP.

## Runtime model

- Bootstrap script: `scripts/run_kumiho_mcp.py`
- Runtime home:
  - Windows: `%LOCALAPPDATA%\\kumiho-cowork`
  - Linux/macOS: `$XDG_CACHE_HOME/kumiho-cowork` or `~/.cache/kumiho-cowork`
- Override runtime home with: `KUMIHO_COWORK_HOME`
- Override package spec with: `KUMIHO_COWORK_PACKAGE_SPEC`

Default package spec:

```text
kumiho[mcp]>=0.9.5 kumiho-memory[all]>=0.1.1
```

## Authentication setup

There are two independent ways to authenticate. Use whichever fits your
workflow — or run `/kumiho-auth` and it will walk you through both options.

### Method A — Dashboard API token (recommended)

Mint a long-lived API token from the [kumiho.io dashboard](https://kumiho.io)
under **API Keys**. Then either:

1. Run the interactive command inside Claude Code:

   ```text
   /kumiho-auth
   ```

2. Or cache it from the command line:

   ```bash
   echo 'eyJ...' | python ./kumiho-cowork/scripts/cache_auth_token.py --stdin
   ```

Both store the token under the `api_token` key in
`~/.kumiho/kumiho_authentication.json`. It does **not** overwrite session
tokens from `kumiho-cli login`.

### Method B — CLI login (email + password)

```bash
kumiho-cli login
```

This creates `~/.kumiho/kumiho_authentication.json` with `id_token` and
`control_plane_token`. These are session tokens and expire — refresh it with
`kumiho-cli refresh` when they do.

### Alternative: environment variable

Set `KUMIHO_AUTH_TOKEN` in your Claude environment
(`.claude/settings.local.json`):

```json
{
  "env": {
    "KUMIHO_AUTH_TOKEN": "YOUR_KUMIHO_BEARER_JWT",
    "KUMIHO_CONTROL_PLANE_URL": "https://control.kumiho.cloud",
    "KUMIHO_MCP_LOG_LEVEL": "INFO"
  }
}
```

> **Note:** Some Claude Code host environments do not propagate
> `settings.local.json` env values to MCP subprocess environments. If your
> token is not picked up via this method, use `/kumiho-auth` or the credential
> cache script above instead.

### Token resolution order

The launcher resolves authentication from these sources (first match wins):

1. Process environment variable `KUMIHO_AUTH_TOKEN`
2. `.claude/settings.local.json` then `.claude/settings.json` (project, then home)
3. `.mcp.json` env block
4. `~/.kumiho/kumiho_authentication.json` credential cache — checks keys in order: `control_plane_token`, `id_token`, `api_token`

Both raw JWT and `"Bearer <jwt>"` formats are accepted.
The plugin starts without a token so tools remain visible, but authenticated
memory/graph operations require a valid token.
Discovery bootstrap tries multiple token candidates before giving up.
If needed, discovery request user-agent can be overridden with
`KUMIHO_COWORK_DISCOVERY_USER_AGENT`.

For higher-quality summarization, set either:
- `OPENAI_API_KEY` (default provider path), or
- `ANTHROPIC_API_KEY` with `KUMIHO_LLM_PROVIDER=anthropic`.

If no LLM key is set, the launcher enables a local fail-fast fallback so MCP
tools still initialize without external LLM credentials.

## Conversation artifacts

The plugin follows a **BYO-storage** model: raw conversation content is stored
locally as Markdown files; the cloud graph stores only metadata and artifact
pointers. This aligns with the Graph-Native Cognitive Memory architecture
(Principle 11: Metadata Over Content).

Artifacts are saved to `~/.kumiho/artifacts/{YYYY-MM-DD}/` by default.
Override with `KUMIHO_ARTIFACT_DIR`:

```bash
# Project-local artifacts:
export KUMIHO_ARTIFACT_DIR=.kumiho/artifacts
```

Each session with 2+ meaningful exchanges produces a Markdown artifact with
YAML frontmatter (session_id, user_id, agent_name, date, topics, summary)
and structured `## Exchange N` sections.

## Troubleshooting

### Token not picked up

If the bootstrap logs:

```text
[kumiho-cowork] Searched N settings paths; none contained a usable env block.
```

Your `settings.local.json` is not being found or doesn't contain an `env`
block. Use `/kumiho-auth` to cache the token directly, or run:

```bash
echo 'YOUR_JWT' | python ./kumiho-cowork/scripts/cache_auth_token.py --stdin
```

### Auth error (401)

If you see:

```text
Memory proxy error 401: {"error":"invalid_id_token"}
```

then your token is invalid for the deployed control-plane auth path.

Fix options:

1. Use a fresh dashboard-minted token via `/kumiho-auth`.
2. Ensure control-plane `/api/memory/redis` is deployed with control-plane token verification.

### Connection refused

If you see:

```text
StatusCode.UNAVAILABLE ... 127.0.0.1:8080 ... Connection refused
```

then Kumiho SDK discovery did not resolve a cloud gRPC endpoint and the SDK
could not bootstrap routing from control-plane.

Fix options:
1. Ensure `KUMIHO_CONTROL_PLANE_URL` points to your deployed control plane.
2. Ensure `/api/discovery/tenant` is deployed with control-plane token verification.

If you see DNS failures for `us-central.kumiho.cloud`, a stale endpoint override is
likely present. This plugin ignores `KUMIHO_SERVER_ENDPOINT`/`KUMIHO_SERVER_ADDRESS`
and resolves endpoint from control-plane on every startup.

## Local validation and smoke test

From repository root:

```bash
claude plugin validate ./kumiho-cowork/.claude-plugin/plugin.json
claude plugin validate ./kumiho-cowork/.claude-plugin/marketplace.json
# optional but recommended for full auth-path verification:
export KUMIHO_AUTH_TOKEN=YOUR_KUMIHO_BEARER_JWT
python ./kumiho-cowork/scripts/run_kumiho_mcp.py --self-test
```

The self-test provisions the runtime and verifies required modules.

## Discovery test with .env.local

Create a `.env.local` file:

```dotenv
KUMIHO_AUTH_TOKEN=eyJ...your-jwt...
KUMIHO_CONTROL_PLANE_URL=https://control.kumiho.cloud
# optional:
# KUMIHO_TENANT_HINT=your-tenant-slug
```

Or start from template:

```bash
cp ./kumiho-cowork/.env.local.example ./.env.local
```

PowerShell:

```powershell
Copy-Item .\kumiho-cowork\.env.local.example .\.env.local
```

Run:

```bash
python ./kumiho-cowork/scripts/test_discovery_env.py --env-file .env.local
```

The script prints `resolved_target` and exits non-zero if discovery resolves
to localhost or cannot resolve a valid Kumiho server target.

## Local usage

Install from local marketplace:

```bash
claude plugin marketplace add ./kumiho-cowork
claude plugin install kumiho-memory@kumiho-cowork --scope local
```

Or run ad hoc without installing:

```bash
claude --plugin-dir ./kumiho-cowork
```

Then verify Kumiho memory tools are available:
- `kumiho_chat_add`
- `kumiho_chat_get`
- `kumiho_chat_clear`
- `kumiho_memory_ingest`
- `kumiho_memory_recall`
- `kumiho_memory_consolidate`
- `kumiho_memory_dream_state`

## Structure

```text
.
├── .claude-plugin/plugin.json
├── .claude-plugin/marketplace.json
├── .mcp.json
├── commands/
│   ├── memory-capture.md
│   ├── kumiho-auth.md
│   └── dream-state.md
├── skills/kumiho-memory/SKILL.md
└── scripts/
    ├── run_kumiho_mcp.py
    ├── cache_auth_token.py
    └── test_discovery_env.py
```
