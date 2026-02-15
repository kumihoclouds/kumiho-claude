#!/usr/bin/env python3
"""Patch .mcp.json with an actual KUMIHO_AUTH_TOKEN value.

On Claude Desktop (macOS), the host does NOT expand shell-style
``${VAR:-default}`` templates in the env block of ``.mcp.json``.
Writing the real token into the file serves two purposes:

1. The MCP server process receives the token via its environment on
   next launch (no fallback hunt needed).
2. Claude Desktop detects the file change and **restarts the MCP server
   process**, which is the actual fix — without a restart, a token
   cached mid-session is never picked up by the already-running server.

Usage:
    python patch_mcp_json_token.py --token eyJ...
    python patch_mcp_json_token.py --from-cache
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path


def _plugin_root() -> Path:
    from_env = (os.getenv("CLAUDE_PLUGIN_ROOT", "") or "").strip()
    if from_env:
        return Path(from_env).expanduser()
    return Path(__file__).resolve().parents[1]


def _mcp_json_path() -> Path:
    return _plugin_root() / ".mcp.json"


def _clean_token(raw: str) -> str:
    token = raw.strip()
    if not token:
        return ""
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        token = token[1:-1].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _is_valid_jwt(token: str) -> bool:
    parts = token.split(".")
    if len(parts) != 3:
        return False
    try:
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode((payload + padding).encode("utf-8"))
        claims = json.loads(decoded.decode("utf-8"))
        return isinstance(claims, dict)
    except Exception:
        return False


def _load_token_from_cache() -> str:
    """Read the best available token from ~/.kumiho/kumiho_authentication.json."""
    config_dir = (os.getenv("KUMIHO_CONFIG_DIR", "") or "").strip()
    if config_dir:
        path = Path(config_dir).expanduser() / "kumiho_authentication.json"
    else:
        path = Path.home() / ".kumiho" / "kumiho_authentication.json"

    if not path.exists():
        return ""

    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""

    if not isinstance(body, dict):
        return ""

    for key in ("api_token", "control_plane_token", "id_token"):
        raw = body.get(key)
        if isinstance(raw, str):
            token = _clean_token(raw)
            if token and _is_valid_jwt(token):
                return token

    return ""


def patch_mcp_json(token: str) -> bool:
    """Write *token* into .mcp.json and return True on success."""
    mcp_path = _mcp_json_path()
    if not mcp_path.exists():
        print(f"Error: {mcp_path} does not exist.", file=sys.stderr)
        return False

    try:
        body = json.loads(mcp_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Error reading {mcp_path}: {exc}", file=sys.stderr)
        return False

    servers = body.get("mcpServers")
    if not isinstance(servers, dict):
        print("Error: .mcp.json missing mcpServers.", file=sys.stderr)
        return False

    server = servers.get("kumiho-memory")
    if not isinstance(server, dict):
        print("Error: .mcp.json missing kumiho-memory server.", file=sys.stderr)
        return False

    env = server.get("env")
    if not isinstance(env, dict):
        env = {}
        server["env"] = env

    old_value = env.get("KUMIHO_AUTH_TOKEN", "")
    env["KUMIHO_AUTH_TOKEN"] = token

    try:
        mcp_path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"Error writing {mcp_path}: {exc}", file=sys.stderr)
        return False

    if old_value == token:
        print("KUMIHO_AUTH_TOKEN unchanged in .mcp.json (already current).", file=sys.stderr)
    else:
        print(f"Patched KUMIHO_AUTH_TOKEN in {mcp_path}.", file=sys.stderr)
        print(
            "Claude Desktop will detect the change and restart the MCP server.",
            file=sys.stderr,
        )

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patch .mcp.json with a real KUMIHO_AUTH_TOKEN."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--token", help="JWT token to write into .mcp.json")
    group.add_argument(
        "--from-cache",
        action="store_true",
        help="Read the token from ~/.kumiho/kumiho_authentication.json",
    )
    args = parser.parse_args()

    if args.from_cache:
        token = _load_token_from_cache()
        if not token:
            print(
                "Error: no valid token found in credential cache.",
                file=sys.stderr,
            )
            return 1
    else:
        token = _clean_token(args.token)

    if not token:
        print("Error: empty token.", file=sys.stderr)
        return 1

    if not _is_valid_jwt(token):
        print("Error: token does not look like a valid JWT.", file=sys.stderr)
        return 1

    return 0 if patch_mcp_json(token) else 1


if __name__ == "__main__":
    raise SystemExit(main())
