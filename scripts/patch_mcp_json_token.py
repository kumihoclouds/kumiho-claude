#!/usr/bin/env python3
"""Patch MCP config with an actual KUMIHO_AUTH_TOKEN value.

On Claude Desktop, the host does NOT expand shell-style
``${VAR:-default}`` templates in the env block of ``.mcp.json``.
Writing the real token into the config serves two purposes:

1. The MCP server process receives the token via its environment on
   next launch (no fallback hunt needed).
2. Claude Desktop detects the file change and **restarts the MCP server
   process**, which is the actual fix — without a restart, a token
   cached mid-session is never picked up by the already-running server.

The script tries the plugin-local ``.mcp.json`` first.  If that path is
read-only (common on Claude Desktop / Cowork where the plugin root lives
in an immutable package cache), it falls back to the Claude Desktop
global config file (``claude_desktop_config.json``), which lives in the
user's writable AppData / Application Support directory.

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

# MCP server names to look for in config files.
_SERVER_NAMES = ("kumiho-memory", "kumiho")


def _plugin_root() -> Path:
    from_env = (os.getenv("CLAUDE_PLUGIN_ROOT", "") or "").strip()
    if from_env:
        return Path(from_env).expanduser()
    return Path(__file__).resolve().parents[1]


def _mcp_json_path() -> Path:
    return _plugin_root() / ".mcp.json"


def _claude_desktop_config_paths() -> list[Path]:
    """Return platform-specific Claude Desktop global config paths."""
    paths: list[Path] = []
    if os.name == "nt":
        appdata = os.getenv("APPDATA", "")
        if appdata:
            paths.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
    else:
        # macOS
        paths.append(
            Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        )
        # Linux (XDG)
        xdg_config = os.getenv("XDG_CONFIG_HOME", "")
        if xdg_config:
            paths.append(Path(xdg_config) / "Claude" / "claude_desktop_config.json")
        else:
            paths.append(Path.home() / ".config" / "Claude" / "claude_desktop_config.json")
    return paths


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


def _find_server_entry(body: dict) -> dict | None:
    """Locate the kumiho MCP server entry in a parsed config."""
    servers = body.get("mcpServers")
    if not isinstance(servers, dict):
        return None
    for name in _SERVER_NAMES:
        entry = servers.get(name)
        if isinstance(entry, dict):
            return entry
    return None


def _patch_config_file(config_path: Path, token: str) -> bool:
    """Write *token* into the kumiho server env block of *config_path*.

    Returns True on success, False on any error (missing file, no server
    entry, read-only filesystem, etc.).
    """
    if not config_path.exists():
        return False

    try:
        body = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Error reading {config_path}: {exc}", file=sys.stderr)
        return False

    server = _find_server_entry(body)
    if server is None:
        return False

    env = server.get("env")
    if not isinstance(env, dict):
        env = {}
        server["env"] = env

    old_value = env.get("KUMIHO_AUTH_TOKEN", "")
    env["KUMIHO_AUTH_TOKEN"] = token

    try:
        config_path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"Error writing {config_path}: {exc}", file=sys.stderr)
        return False

    if old_value == token:
        print(
            f"KUMIHO_AUTH_TOKEN unchanged in {config_path.name} (already current).",
            file=sys.stderr,
        )
    else:
        print(f"Patched KUMIHO_AUTH_TOKEN in {config_path}.", file=sys.stderr)
        print(
            "Claude Desktop will detect the change and restart the MCP server.",
            file=sys.stderr,
        )

    return True


def patch_mcp_json(token: str) -> bool:
    """Patch the token into the best available MCP config file.

    Tries the plugin-local ``.mcp.json`` first.  If that fails (read-only
    filesystem, missing file, etc.), falls back to the Claude Desktop
    global config file.
    """
    # 1. Try plugin-local .mcp.json
    plugin_path = _mcp_json_path()
    if _patch_config_file(plugin_path, token):
        return True

    # 2. Fallback: Claude Desktop global config
    for desktop_path in _claude_desktop_config_paths():
        if _patch_config_file(desktop_path, token):
            return True

    print(
        "Error: could not patch any MCP config file. "
        f"Tried plugin .mcp.json ({plugin_path}) and Claude Desktop global config.",
        file=sys.stderr,
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patch MCP config with a real KUMIHO_AUTH_TOKEN."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--token", help="JWT token to write into MCP config")
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
