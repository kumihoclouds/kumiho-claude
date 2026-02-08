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
    "KUMIHO_CONTROL_PLANE_URL": "https://control.kumiho.cloud",
    "KUMIHO_MCP_LOG_LEVEL": "INFO"
  }
}
```

`KUMIHO_AUTH_TOKEN` should be a bearer JWT (three-part token format).

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

then your token is invalid for the deployed control-plane auth path.

Fix options:
1. Use a fresh dashboard-minted `KUMIHO_AUTH_TOKEN`.
2. Ensure control-plane `/api/memory/redis` is deployed with control-plane token verification.

If you see:

```text
StatusCode.UNAVAILABLE ... 127.0.0.1:8080 ... Connection refused
```

then Kumiho SDK discovery did not resolve a cloud gRPC endpoint and the SDK
fell back to local default.

Fix options:
1. Ensure `KUMIHO_CONTROL_PLANE_URL` points to your deployed control plane.
2. Ensure `/api/discovery/tenant` is deployed with control-plane token verification.

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

