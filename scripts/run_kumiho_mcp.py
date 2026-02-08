#!/usr/bin/env python3
"""Bootstrap and run Kumiho MCP server for Claude plugin environments."""

from __future__ import annotations

import argparse
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
    token = os.getenv("KUMIHO_AUTH_TOKEN", "").strip()
    token_file = os.getenv("KUMIHO_AUTH_TOKEN_FILE", "").strip()
    if token or token_file:
        return
    print(
        "[kumiho-cowork] Warning: KUMIHO_AUTH_TOKEN is not set. "
        "The server may rely on cached auth from kumiho-auth login.",
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
