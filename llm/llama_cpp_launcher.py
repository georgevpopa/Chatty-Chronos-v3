"""llama.cpp auto-launcher — detects GPU and starts the right binary.

Resolves the llama-server binary generically so it works on any machine:
1. explicit path passed in / config `local_server_bin`
2. env var CHRONOS_LLAMA_SERVER
3. `llama-server` (or `llama-server.exe`) found on PATH
No machine-specific paths are hardcoded. AMD ROCm/HIP env vars are opt-in.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _binary_name() -> str:
    return "llama-server.exe" if os.name == "nt" else "llama-server"


def detect_gpu_backend() -> str:
    """Detect the best GPU backend for this system.

    Returns 'hip' for AMD GPUs, 'vulkan' otherwise (universal fallback).
    """
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["wmic", "path", "win32_videocontroller", "get", "name"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.lower()
        else:
            # Linux: inspect lspci / /sys if available
            result = subprocess.run(["sh", "-c", "lspci 2>/dev/null || true"],
                                    capture_output=True, text=True, timeout=10)
            output = result.stdout.lower()
        if "amd" in output or "radeon" in output:
            return "hip"
    except Exception:
        pass
    return "vulkan"


def get_server_binary(backend: str | None = None, explicit_path: str | None = None) -> Path | None:
    """Resolve the llama-server binary path without hardcoding machine paths.

    Resolution order:
      1. explicit_path argument (from config `local_server_bin`)
      2. env var CHRONOS_LLAMA_SERVER
      3. `llama-server` on the system PATH
    Returns Path if found and existing, else None.
    """
    # 1. explicit path (e.g. from config)
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return p

    # 2. environment variable override
    env_path = os.environ.get("CHRONOS_LLAMA_SERVER")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    # 3. on PATH
    found = shutil.which(_binary_name()) or shutil.which("llama-server")
    if found:
        return Path(found)

    return None


def start_server(
    model_path: str,
    port: int = 8080,
    n_gpu_layers: int = -1,
    context_size: int = 4096,
    backend: str | None = None,
    binary_path: str | None = None,
    extra_env: dict | None = None,
) -> subprocess.Popen | None:
    """Start llama-server as a background process.

    Args:
        binary_path: explicit path to llama-server (from config `local_server_bin`).
        extra_env: additional environment variables (e.g. AMD ROCm overrides). These
                   are opt-in and supplied by the caller/config — nothing is hardcoded.

    Returns the Popen object, or None if the binary wasn't found.
    """
    binary = get_server_binary(backend, explicit_path=binary_path)
    if binary is None:
        print("ERROR: No llama-server binary found.", file=sys.stderr)
        print("Set it via config `local_server_bin`, the CHRONOS_LLAMA_SERVER env "
              "var, or put `llama-server` on your PATH.", file=sys.stderr)
        return None

    cmd = [
        str(binary),
        "-m", model_path,
        "--port", str(port),
        "-ngl", str(n_gpu_layers),
        "-c", str(context_size),
        "--host", "0.0.0.0",
    ]

    # Environment: start from current, apply any user-supplied overrides (opt-in).
    env = None
    if extra_env:
        env = os.environ.copy()
        env.update({str(k): str(v) for k, v in extra_env.items()})

    print(f"Starting llama-server ({backend or detect_gpu_backend()})...")
    print(f"  Binary: {binary}")
    print(f"  Model:  {model_path}")
    print(f"  Port:   {port}")

    return subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def is_server_running(port: int = 8080) -> bool:
    """Check if a llama-server is already running on the given port."""
    import httpx
    try:
        resp = httpx.get(f"http://localhost:{port}/health", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False
