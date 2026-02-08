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
kumiho[mcp]>=0.9.4 kumiho-memory[all]>=0.1.1
```

## Required environment

Set these in your Claude environment (recommended in `.claude/settings.local.json`):

```json
{
  "env": {
    "KUMIHO_AUTH_TOKEN": "YOUR_KUMIHO_BEARER_JWT",
    "KUMIHO_FIREBASE_ID_TOKEN": "YOUR_FIREBASE_ID_TOKEN",
    "KUMIHO_CONTROL_PLANE_URL": "https://control.kumiho.cloud",
    "KUMIHO_MCP_LOG_LEVEL": "INFO"
  }
}
```

`KUMIHO_AUTH_TOKEN_FILE` is also supported as an alternative to inline token.
`KUMIHO_AUTH_TOKEN` should be a bearer JWT (three-part token format).

`kumiho-memory` proxy endpoints on older control-plane versions require a
Firebase ID token. If your control-plane is updated to accept service/control-plane
tokens for `/api/memory/redis`, dashboard API tokens also work directly.

If you prefer cached auth instead of token env, run `kumiho-auth login` once
on your machine and omit `KUMIHO_AUTH_TOKEN`.

For higher-quality summarization, set either:
- `OPENAI_API_KEY` (default provider path), or
- `ANTHROPIC_API_KEY` with `KUMIHO_LLM_PROVIDER=anthropic`.

If no LLM key is set, the launcher enables a local fail-fast fallback so MCP
tools still initialize without external LLM credentials.

## Troubleshooting

If you see:

```text
Memory proxy error 401: {"error":"invalid_id_token"}
```

then your token type is likely not a Firebase ID token for proxy auth.

Fix options:
1. Update control-plane `/api/memory/redis` to accept control-plane/service tokens.
2. Set `KUMIHO_FIREBASE_ID_TOKEN` to a valid Firebase ID token for your user.
3. Run `kumiho-auth login` to cache Firebase credentials locally.

## Local validation and smoke test

From repository root:

```bash
claude plugin validate ./kumiho-cowork/.claude-plugin/plugin.json
claude plugin validate ./kumiho-cowork/.claude-plugin/marketplace.json
python ./kumiho-cowork/scripts/run_kumiho_mcp.py --self-test
```

The self-test provisions the runtime and verifies required modules.

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
- `kumiho_memory_ingest`
- `kumiho_memory_recall`
- `kumiho_memory_consolidate`

## Structure

```text
.
├── .claude-plugin/plugin.json
├── .claude-plugin/marketplace.json
├── .mcp.json
├── commands/memory-capture.md
├── skills/kumiho-memory/SKILL.md
└── scripts/run_kumiho_mcp.py
```

