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
import urllib.error
import urllib.parse
import urllib.request
import venv
from pathlib import Path


DEFAULT_PACKAGE_SPEC = "kumiho[mcp]>=0.9.5 kumiho-memory[all]>=0.1.1"
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
    if auth_token:
        return
    print(
        "[kumiho-cowork] Warning: KUMIHO_AUTH_TOKEN is not set. "
        "Memory and graph operations will fail until a token is provided.",
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


def _validate_auth_token() -> None:
    auth_token = os.getenv("KUMIHO_AUTH_TOKEN", "").strip()
    if not auth_token:
        return

    claims = _decode_jwt_claims(auth_token)
    if claims:
        return

    print(
        "[kumiho-cowork] Warning: KUMIHO_AUTH_TOKEN does not look like a JWT. "
        "Use a dashboard-minted Kumiho API token.",
        file=sys.stderr,
    )


def _load_bearer_token() -> str:
    return os.getenv("KUMIHO_AUTH_TOKEN", "").strip()


def _build_discovery_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/api/discovery/tenant"):
        return base
    if base.endswith("/api/discovery"):
        return f"{base}/tenant"
    if base.endswith("/api"):
        return f"{base}/discovery/tenant"
    return f"{base}/api/discovery/tenant"


def _normalize_server_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if not target:
        return None

    if "://" in target:
        parsed = urllib.parse.urlparse(target)
        if not parsed.hostname:
            return None
        scheme = parsed.scheme.lower()
        port = parsed.port
        if port is None:
            if scheme in {"https", "grpcs"}:
                port = 443
            elif scheme in {"http", "grpc"}:
                port = 80
            else:
                port = 443
        return f"{parsed.hostname}:{port}"

    if "/" in target:
        target = target.split("/", 1)[0]
    return target or None


def _bootstrap_server_endpoint() -> None:
    preset_endpoint = os.getenv("KUMIHO_SERVER_ENDPOINT", "").strip() or os.getenv("KUMIHO_SERVER_ADDRESS", "").strip()
    if preset_endpoint:
        print(
            "[kumiho-cowork] Ignoring pre-set KUMIHO_SERVER_ENDPOINT/KUMIHO_SERVER_ADDRESS; "
            "resolving endpoint via control-plane discovery.",
            file=sys.stderr,
        )
    # Always clear any inherited endpoint so startup cannot lock onto stale routing.
    os.environ.pop("KUMIHO_SERVER_ENDPOINT", None)
    os.environ.pop("KUMIHO_SERVER_ADDRESS", None)

    bearer = _load_bearer_token()
    if not bearer:
        print(
            "[kumiho-cowork] KUMIHO_AUTH_TOKEN is not set; skipping discovery bootstrap. "
            "MCP tools will load, but authenticated calls will fail until token is provided.",
            file=sys.stderr,
        )
        return

    control_plane_url = os.getenv("KUMIHO_CONTROL_PLANE_URL", "").strip() or "https://control.kumiho.cloud"
    discovery_url = _build_discovery_url(control_plane_url)
    tenant_hint = os.getenv("KUMIHO_TENANT_HINT", "").strip()

    payload: dict[str, str] = {}
    if tenant_hint:
        payload["tenant_hint"] = tenant_hint

    request = urllib.request.Request(
        discovery_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body_text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = ""
        detail = detail.strip().replace("\n", " ")
        if detail:
            detail = f" {detail[:160]}"
        print(
            f"[kumiho-cowork] Discovery bootstrap skipped ({exc.code}).{detail}",
            file=sys.stderr,
        )
        raise RuntimeError("Control-plane discovery failed; refusing endpoint fallback.") from exc
    except Exception as exc:
        raise RuntimeError(f"Control-plane discovery request failed: {exc}") from exc

    try:
        body = json.loads(body_text)
    except json.JSONDecodeError:
        raise RuntimeError("Control-plane discovery returned invalid JSON.")

    region = body.get("region")
    if not isinstance(region, dict):
        raise RuntimeError("Control-plane discovery response missing region routing.")

    raw_target = ""
    grpc_authority = region.get("grpc_authority")
    if isinstance(grpc_authority, str) and grpc_authority.strip():
        raw_target = grpc_authority
    else:
        server_url = region.get("server_url")
        if isinstance(server_url, str) and server_url.strip():
            raw_target = server_url

    resolved_target = _normalize_server_target(raw_target)
    if not resolved_target:
        raise RuntimeError("Control-plane discovery response missing gRPC target.")

    os.environ["KUMIHO_SERVER_ENDPOINT"] = resolved_target
    os.environ.pop("KUMIHO_SERVER_ADDRESS", None)
    print(
        f"[kumiho-cowork] Resolved KUMIHO_SERVER_ENDPOINT={resolved_target} via discovery bootstrap.",
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

    _validate_auth_token()
    _warn_auth()
    try:
        _bootstrap_server_endpoint()
    except RuntimeError as exc:
        print(
            "[kumiho-cowork] Discovery bootstrap failed. "
            "Starting MCP server without pre-resolved endpoint. "
            f"Error: {exc}",
            file=sys.stderr,
        )
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
