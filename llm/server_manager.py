"""Local llama-server process lifecycle manager.

Automatically launches and terminates llama-server.exe with AMD HIP/ROCm environment settings.
"""
import subprocess
import time
import os
import sys
import httpx
from rich.console import Console
from core.config import Config

console = Console()
_process = None


def is_available(host: str) -> bool:
    """Check if the llama-server is responsive."""
    try:
        with httpx.Client(timeout=1) as client:
            r = client.get(f"{host}/health")
            # /health returns 200 OK
            return r.status_code == 200
    except Exception:
        return False


def start_local_server(config: Config):
    """Start the local llama-server in the background if enabled and not already running."""
    global _process
    if not config.get("local_server_enabled", False):
        return

    host = config.get("llamacpp_host", "http://localhost:8080")
    model_path = config.get("local_server_model")
    model_filename = os.path.basename(model_path) if model_path else ""

    if is_available(host):
        running_model = ""
        try:
            with httpx.Client(timeout=2) as client:
                r = client.get(f"{host}/v1/models")
                if r.status_code == 200:
                    data = r.json()
                    if "data" in data and len(data["data"]) > 0:
                        running_model = data["data"][0].get("id", "")
        except Exception:
            pass

        mismatch = False
        if running_model and model_filename:
            if model_filename.lower() not in running_model.lower():
                mismatch = True

        if mismatch:
            console.print(f"  [yellow]⚠ Model mismatch detected on port {host}![/yellow]")
            console.print(f"    Configured: [cyan]{model_filename}[/cyan]")
            console.print(f"    Running:    [yellow]{os.path.basename(running_model)}[/yellow]")
            console.print(f"  [cyan]Attempting to terminate the mismatched server...[/cyan]")
            if sys.platform == "win32":
                os.system("taskkill /f /im llama-server.exe >nul 2>&1")
            else:
                os.system("pkill -f llama-server >/dev/null 2>&1")
            time.sleep(2)
        else:
            console.print(f"  [green]● Local llama-server already running at {host}[/green]")
            return

    bin_path = config.get("local_server_bin")
    model_path = config.get("local_server_model")
    port = config.get("local_server_port", 8080)
    ngl = config.get("local_server_ngl", 99)
    ctx = config.get("local_server_ctx", 4096)

    if not bin_path:
        console.print("  [red]FAIL: 'local_server_bin' configuration is empty.[/red]")
        return

    # Expand user variables
    bin_path = os.path.expandvars(bin_path)
    if not os.path.exists(bin_path):
        console.print(f"  [red]FAIL: Local server executable not found at '{bin_path}'[/red]")
        return

    if not model_path:
        console.print("  [red]FAIL: 'local_server_model' configuration is empty.[/red]")
        return

    model_path = os.path.expandvars(model_path)
    if not os.path.exists(model_path):
        console.print(f"  [red]FAIL: GGUF model file not found at '{model_path}'[/red]")
        return

    # Build command line
    parallel = config.get("local_server_parallel", 1)
    reasoning_budget = config.get("local_server_reasoning_budget", 1024)
    cache_ram = config.get("local_server_cache_ram", 512)

    cmd = [
        bin_path,
        "-m", model_path,
        "--port", str(port),
        "-ngl", str(ngl),
        "-c", str(ctx),
        "--parallel", str(parallel),
        "--split-mode", "none",
    ]

    # Optional flags (only add if configured and supported by the build)
    if reasoning_budget is not None:
        cmd.extend(["--reasoning-budget", str(reasoning_budget)])
    if cache_ram is not None:
        cmd.extend(["--cache-ram", str(cache_ram)])

    # Setup environment variables (e.g. HSA_OVERRIDE_GFX_VERSION and HIP_VISIBLE_DEVICES)
    env = os.environ.copy()
    custom_env = config.get("local_server_env", {})
    if custom_env:
        for k, v in custom_env.items():
            env[str(k)] = str(v)

    console.print(f"  [cyan]Starting local llama-server...[/cyan]")
    console.print(f"    Exec:  {bin_path}")
    console.print(f"    Model: {os.path.basename(model_path)}")

    try:
        # Ensure log directory exists
        log_dir = config.dir / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "llama_server.log"

        # Redirect stdout/stderr to log file
        f_log = open(log_file, "w", encoding="utf-8")

        # Start background subprocess without showing window (on Windows)
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        
        _process = subprocess.Popen(
            cmd,
            env=env,
            stdout=f_log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags
        )

        # Wait for the server to spin up and bind (30 seconds maximum)
        console.print(f"  [dim]Waiting for llama-server to bind (log: {log_file})...[/dim]")
        for _ in range(30):
            time.sleep(1)
            if is_available(host):
                console.print(f"  [green]✓ Local llama-server connected successfully![/green]")
                return
            # If the process terminates early, notify the user
            if _process.poll() is not None:
                console.print(f"  [red]FAIL: llama-server process exited early with code {_process.returncode}[/red]")
                f_log.close()
                try:
                    log_text = log_file.read_text(encoding="utf-8")
                    lines = log_text.splitlines()[-15:]
                    console.print("\n[dim]Last 15 lines of llama_server.log:[/dim]")
                    for line in lines:
                        console.print(f"    [red]{line}[/red]")
                        
                    # Check for VRAM/HIP/CUDA memory allocation errors
                    log_lower = log_text.lower()
                    if "vram" in log_lower or "out of memory" in log_lower or "hip error" in log_lower or "cuda error" in log_lower:
                        console.print("\n  [bold yellow]💡 GPU Optimization Tip:[/bold yellow]")
                        console.print("    A VRAM allocation issue was detected in llama-server. On shared/integrated GPUs")
                        console.print("    (like the AMD Radeon 890M), over-allocating GPU layers can crash the runtime.")
                        console.print("    Try [cyan]reducing 'local_server_ngl'[/cyan] in your config (e.g. set it to 30 or 40)")
                        console.print("    to distribute layers safely between GPU and system RAM.\n")
                except Exception:
                    pass
                return

        console.print(f"  [yellow]WARN: Server process started but did not respond yet at {host}[/yellow]")
    except Exception as e:
        console.print(f"  [red]Error launching llama-server: {e}[/red]")


def stop_local_server():
    """Terminate the background llama-server process."""
    global _process
    if _process and _process.poll() is None:
        console.print(f"  [cyan]Stopping local llama-server...[/cyan]")
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
        console.print("  [dim]llama-server stopped.[/dim]")
        _process = None
    # Also kill any orphaned llama-server processes
    if sys.platform == "win32":
        os.system("taskkill /f /im llama-server.exe >nul 2>&1")
    else:
        os.system("pkill -f llama-server >/dev/null 2>&1")


def restart_with_model(config, model_name):
    """Stop current server, update config, and start with new model."""
    stop_local_server()
    time.sleep(2)

    # Find the full path for this GGUF file
    models_dir = config.get("local_server_model", "")
    if models_dir:
        models_dir = os.path.dirname(models_dir)

    new_model_path = os.path.join(models_dir, model_name)
    if not os.path.exists(new_model_path):
        console.print(f"  [red]Model file not found: {new_model_path}[/red]")
        return False

    # Update config
    config.set("local_server_model", new_model_path)
    config.set("model", model_name)

    console.print(f"  [cyan]Starting llama-server with {model_name}...[/cyan]")
    start_local_server(config)
    return True


def get_system_telemetry():
    """Return memory and server process diagnostic telemetry."""
    telemetry = {
        "ram_total": 0,
        "ram_used": 0,
        "ram_free": 0,
        "ram_load": 0,
        "server_pid": None,
        "server_memory_mb": 0,
        "platform": sys.platform
    }
    
    global _process
    if _process and _process.poll() is None:
        telemetry["server_pid"] = _process.pid
        
    if sys.platform == "win32":
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        try:
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            telemetry["ram_total"] = round(stat.ullTotalPhys / (1024 ** 3), 1)
            telemetry["ram_free"] = round(stat.ullAvailPhys / (1024 ** 3), 1)
            telemetry["ram_used"] = round(telemetry["ram_total"] - telemetry["ram_free"], 1)
            telemetry["ram_load"] = stat.dwMemoryLoad
            
            if telemetry["server_pid"]:
                cmd = f'wmic process where processid={telemetry["server_pid"]} get WorkingSetSize /value'
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                for line in res.stdout.splitlines():
                    if "WorkingSetSize" in line:
                        bytes_val = int(line.split("=")[1].strip())
                        telemetry["server_memory_mb"] = round(bytes_val / (1024 * 1024), 1)
        except Exception:
            pass
    else:
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            total_kb = 0
            free_kb = 0
            for line in lines:
                if "MemTotal" in line:
                    total_kb = int(line.split()[1])
                elif "MemAvailable" in line:
                    free_kb = int(line.split()[1])
            if total_kb:
                telemetry["ram_total"] = round(total_kb / (1024 * 1024), 1)
                telemetry["ram_free"] = round(free_kb / (1024 * 1024), 1)
                telemetry["ram_used"] = round(telemetry["ram_total"] - telemetry["ram_free"], 1)
                telemetry["ram_load"] = int((telemetry["ram_used"] / telemetry["ram_total"]) * 100)
                
            if telemetry["server_pid"]:
                with open(f"/proc/{telemetry['server_pid']}/status", "r") as f:
                    for line in f:
                        if "VmRSS" in line:
                            rss_kb = int(line.split()[1])
                            telemetry["server_memory_mb"] = round(rss_kb / 1024, 1)
                            break
        except Exception:
            pass
            
    return telemetry
