# Kumiho Memory — Plugin for Claude Code & Cowork

Persistent graph-native memory plugin for Claude. Runs a local Kumiho MCP
server with `kumiho-memory` — works in both **Claude Code** (CLI) and
**Claude Cowork** (desktop autonomous agent).

## What it does

- Bootstraps user identity and preferences at session start
- Recalls context from previous sessions via semantic graph search
- Stores decisions, preferences, and project facts automatically
- Generates local conversation artifacts (BYO-storage model)
- Runs Dream State consolidation for memory hygiene

## Platform compatibility

| Feature | Claude Code | Claude Cowork |
| ------- | ----------- | ------------- |
| MCP memory tools | Yes | Yes |
| Session bootstrap | Yes | Yes |
| Artifact generation | Yes | Yes |
| `/kumiho-auth` command | Yes | Yes |
| `/memory-capture` command | Yes | Yes |
| `/dream-state` command | Yes | Yes |
| Auto-approve memory ops | Yes | No (Cowork manages permissions differently) |
| `.claude/settings.json` auth | Yes | No (use `.env.local` instead) |

## Installation

### Claude Cowork

Install from the [plugin marketplace](https://claude.com/plugins-for/cowork),
or upload the plugin directory manually in the Cowork settings.

### Claude Code

Install from local marketplace:

```bash
claude plugin marketplace add ./kumiho-cowork
claude plugin install kumiho-memory@kumiho-cowork --scope local
```

Or run ad hoc without installing:

```bash
claude --plugin-dir ./kumiho-cowork
```

## Runtime model

- Bootstrap script: `scripts/run_kumiho_mcp.py`
- Runtime home:
  - Windows: `%LOCALAPPDATA%\kumiho-cowork`
  - macOS/Linux: `$XDG_CACHE_HOME/kumiho-cowork` or `~/.cache/kumiho-cowork`
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

1. Run the interactive command inside Claude:

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
`control_plane_token`. These are session tokens and expire — refresh with
`kumiho-cli refresh` when they do.

### Alternative: environment variable

Set `KUMIHO_AUTH_TOKEN` in `.env.local` at the plugin root:

```dotenv
KUMIHO_AUTH_TOKEN=YOUR_KUMIHO_BEARER_JWT
KUMIHO_CONTROL_PLANE_URL=https://control.kumiho.cloud
```

In Claude Code, you can also set it in `.claude/settings.local.json`:

```json
{
  "env": {
    "KUMIHO_AUTH_TOKEN": "YOUR_KUMIHO_BEARER_JWT",
    "KUMIHO_CONTROL_PLANE_URL": "https://control.kumiho.cloud"
  }
}
```

### Token resolution order

The launcher resolves authentication from these sources (first match wins):

1. Process environment variable `KUMIHO_AUTH_TOKEN`
2. `.env.local` at the plugin root
3. `.claude/settings.local.json` then `.claude/settings.json` *(Claude Code only)*
4. `.mcp.json` env block
5. `~/.kumiho/kumiho_authentication.json` credential cache — checks keys in order: `control_plane_token`, `id_token`, `api_token`

Both raw JWT and `"Bearer <jwt>"` formats are accepted.
The plugin starts without a token so tools remain visible, but authenticated
memory/graph operations require a valid token.

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
export KUMIHO_ARTIFACT_DIR=.kumiho/artifacts
```

Each session with 2+ meaningful exchanges produces a Markdown artifact with
YAML frontmatter (session_id, date, topics, summary) and structured
`## Exchange N` sections.

## Troubleshooting

### Token not picked up

If the bootstrap logs:

```text
[kumiho-cowork] Searched N settings paths; none contained a usable env block.
```

Use `/kumiho-auth` to cache the token directly, or run:

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

then Kumiho SDK discovery did not resolve a cloud gRPC endpoint.

Fix options:

1. Ensure `KUMIHO_CONTROL_PLANE_URL` points to your deployed control plane.
2. Ensure `/api/discovery/tenant` is deployed with control-plane token verification.

If you see DNS failures for `us-central.kumiho.cloud`, a stale endpoint override is
likely present. This plugin ignores `KUMIHO_SERVER_ENDPOINT`/`KUMIHO_SERVER_ADDRESS`
and resolves endpoint from control-plane on every startup.

## Validation and smoke test

```bash
# Claude Code only — validate plugin manifest:
claude plugin validate ./kumiho-cowork/.claude-plugin/plugin.json

# Both platforms — provision runtime and verify required modules:
export KUMIHO_AUTH_TOKEN=YOUR_KUMIHO_BEARER_JWT
python ./kumiho-cowork/scripts/run_kumiho_mcp.py --self-test
```

## Discovery test with .env.local

Create a `.env.local` file (or copy from template):

```bash
cp ./kumiho-cowork/.env.local.example ./.env.local
```

Run:

```bash
python ./kumiho-cowork/scripts/test_discovery_env.py --env-file .env.local
```

The script prints `resolved_target` and exits non-zero if discovery resolves
to localhost or cannot resolve a valid Kumiho server target.

## Structure

```text
.
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── .mcp.json
├── commands/
│   ├── kumiho-auth.md
│   ├── memory-capture.md
│   └── dream-state.md
├── hooks/
│   └── hooks.json
├── skills/
│   └── kumiho-memory/SKILL.md
└── scripts/
    ├── run_kumiho_mcp.py
    ├── session-bootstrap.py
    ├── save-session-artifact.py
    ├── auto-approve-memory.py
    ├── cache_auth_token.py
    ├── patch_mcp_json_token.py
    └── test_discovery_env.py
```
