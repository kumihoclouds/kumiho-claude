#!/usr/bin/env python3
"""Bootstrap and run Kumiho MCP server for Claude plugin environments."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shlex
import subprocess
import sys
import venv
from pathlib import Path


DEFAULT_PACKAGE_SPEC = "kumiho[mcp]>=0.9.4 kumiho-memory[all]>=0.1.1"
MARKER_FILE = ".installed-packages.txt"


def _state_dir() -> Path:
    override = os.getenv("KUMIHO_COWORK_HOME", "").strip()
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(base) / "kumiho-cowork"

    xdg = os.getenv("XDG_CACHE_HOME", "").strip()
    if xdg:
        return Path(xdg) / "kumiho-cowork"
    return Path.home() / ".cache" / "kumiho-cowork"


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(cmd: list[str], *, check: bool = True) -> int:
    proc = subprocess.run(cmd, check=check)
    return proc.returncode


def _needs_install(python_path: Path, marker_path: Path, package_spec: str) -> bool:
    if not python_path.exists():
        return True

    marker = marker_path.read_text(encoding="utf-8").strip() if marker_path.exists() else ""
    if marker != package_spec:
        return True

    check_code = (
        "import importlib.util,sys;"
        "mods=('kumiho.mcp_server','kumiho_memory');"
        "missing=[m for m in mods if importlib.util.find_spec(m) is None];"
        "sys.exit(1 if missing else 0)"
    )
    try:
        _run([str(python_path), "-c", check_code], check=True)
    except subprocess.CalledProcessError:
        return True
    return False


def _install_dependencies(python_path: Path, package_spec: str) -> None:
    _run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
    packages = shlex.split(package_spec) if package_spec else shlex.split(DEFAULT_PACKAGE_SPEC)
    _run([str(python_path), "-m", "pip", "install", "--upgrade", *packages])


def _ensure_runtime() -> Path:
    package_spec = os.getenv("KUMIHO_COWORK_PACKAGE_SPEC", "").strip() or DEFAULT_PACKAGE_SPEC
    state_dir = _state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)

    venv_dir = state_dir / "venv"
    marker_path = state_dir / MARKER_FILE
    python_path = _venv_python(venv_dir)

    if not python_path.exists():
        print(f"[kumiho-cowork] Creating virtualenv: {venv_dir}", file=sys.stderr)
        venv.create(venv_dir, with_pip=True)

    if _needs_install(python_path, marker_path, package_spec):
        print("[kumiho-cowork] Installing dependencies...", file=sys.stderr)
        _install_dependencies(python_path, package_spec)
        marker_path.write_text(package_spec, encoding="utf-8")

    return python_path


def _warn_auth() -> None:
    auth_token = os.getenv("KUMIHO_AUTH_TOKEN", "").strip()
    firebase_token = os.getenv("KUMIHO_FIREBASE_ID_TOKEN", "").strip()
    token_file = os.getenv("KUMIHO_AUTH_TOKEN_FILE", "").strip()
    if auth_token or firebase_token or token_file:
        return
    print(
        "[kumiho-cowork] Warning: no auth token env is set. "
        "The server may rely on cached auth from kumiho-auth login.",
        file=sys.stderr,
    )


def _decode_jwt_claims(token: str) -> dict | None:
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode((payload + padding).encode("utf-8"))
        claims = json.loads(decoded.decode("utf-8"))
        if isinstance(claims, dict):
            return claims
    except Exception:
        return None
    return None


def _is_control_plane_token(claims: dict) -> bool:
    if isinstance(claims.get("tenant_id"), str):
        return True
    iss = claims.get("iss")
    if isinstance(iss, str) and ("control.kumiho.cloud" in iss or "kumiho.io/control-plane" in iss):
        return True
    aud = claims.get("aud")
    if isinstance(aud, str) and aud.startswith("kumiho-server"):
        return True
    return False


def _is_firebase_id_token(claims: dict) -> bool:
    iss = claims.get("iss")
    if isinstance(iss, str) and iss.startswith("https://securetoken.google.com/"):
        return True
    firebase = claims.get("firebase")
    return isinstance(firebase, dict)


def _normalize_token_envs() -> None:
    auth_token = os.getenv("KUMIHO_AUTH_TOKEN", "").strip()
    firebase_token = os.getenv("KUMIHO_FIREBASE_ID_TOKEN", "").strip()

    if firebase_token and not auth_token:
        os.environ["KUMIHO_AUTH_TOKEN"] = firebase_token
        print(
            "[kumiho-cowork] KUMIHO_AUTH_TOKEN is not set; using KUMIHO_FIREBASE_ID_TOKEN for bearer auth.",
            file=sys.stderr,
        )
        return

    if not auth_token or firebase_token:
        return

    claims = _decode_jwt_claims(auth_token)
    if claims and _is_firebase_id_token(claims):
        os.environ["KUMIHO_FIREBASE_ID_TOKEN"] = auth_token
        print(
            "[kumiho-cowork] KUMIHO_AUTH_TOKEN looks like Firebase ID token; mirroring to KUMIHO_FIREBASE_ID_TOKEN.",
            file=sys.stderr,
        )
        return

    if claims and _is_control_plane_token(claims):
        print(
            "[kumiho-cowork] KUMIHO_AUTH_TOKEN looks like a control-plane token. "
            "If your control plane supports service-token auth for /api/memory/redis this is fine; "
            "otherwise set KUMIHO_FIREBASE_ID_TOKEN or run kumiho-auth login.",
            file=sys.stderr,
        )
        return

    if auth_token.startswith("kh_"):
        print(
            "[kumiho-cowork] KUMIHO_AUTH_TOKEN looks like an API key, not a Firebase JWT. "
            "Memory proxy calls will fail with invalid_id_token.",
            file=sys.stderr,
        )


def _configure_llm_fallback() -> None:
    if os.getenv("KUMIHO_COWORK_DISABLE_LLM_FALLBACK", "").strip().lower() in {"1", "true", "yes"}:
        return

    key_vars = ("KUMIHO_LLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    if any(os.getenv(var, "").strip() for var in key_vars):
        return

    os.environ.setdefault("KUMIHO_LLM_PROVIDER", "openai")
    os.environ.setdefault("OPENAI_API_KEY", "kumiho-cowork-fallback")
    os.environ.setdefault("KUMIHO_LLM_BASE_URL", "http://127.0.0.1:9/v1")
    print(
        "[kumiho-cowork] No LLM API key detected. "
        "Using fail-fast local fallback for summarization.",
        file=sys.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Kumiho MCP with auto-bootstrap.")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Provision runtime and verify required modules, then exit.",
    )
    args, passthrough = parser.parse_known_args()

    _normalize_token_envs()
    _warn_auth()
    _configure_llm_fallback()
    python_path = _ensure_runtime()

    if args.self_test:
        check_code = (
            "import importlib.util,sys;"
            "mods=('kumiho.mcp_server','kumiho_memory');"
            "missing=[m for m in mods if importlib.util.find_spec(m) is None];"
            "print('ok' if not missing else 'missing:' + ','.join(missing));"
            "sys.exit(0 if not missing else 1)"
        )
        return _run([str(python_path), "-c", check_code], check=False)

    cmd = [str(python_path), "-m", "kumiho.mcp_server", *passthrough]
    os.execv(str(python_path), cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
