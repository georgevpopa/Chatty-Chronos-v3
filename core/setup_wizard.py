"""First-run setup wizard — guides a new user to a working config.

Design goals:
- Runs automatically on first launch (no config.json yet), and via /setup anytime.
- ALWAYS skippable (Enter / Ctrl+C) and NEVER blocks startup: any detection failure
  or user skip falls back to a sensible local-first default (Ollama).
- Reuses the existing /add_provider wizard for the cloud path (no duplication).
"""
import os
import shutil
import subprocess
from core import state


def is_first_run() -> bool:
    """True if the user has no config file yet (fresh install)."""
    return not (state.config.dir / "config.json").exists()


def _detect_gpu() -> str:
    """Best-effort GPU vendor detection. Returns 'nvidia' | 'amd' | 'apple' | 'none'."""
    try:
        import platform
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            return "apple"
        # Linux/Windows: inspect lspci / wmic
        if os.name == "nt":
            out = subprocess.run(["wmic", "path", "win32_videocontroller", "get", "name"],
                                 capture_output=True, text=True, timeout=8).stdout.lower()
        else:
            out = subprocess.run(["sh", "-c", "lspci 2>/dev/null || true"],
                                 capture_output=True, text=True, timeout=8).stdout.lower()
        if "nvidia" in out:
            return "nvidia"
        if "amd" in out or "radeon" in out:
            return "amd"
    except Exception:
        pass
    return "none"


def _ollama_status(host: str) -> tuple[bool, list]:
    """Return (running, [model names]) for a local Ollama, without hard deps."""
    try:
        import httpx
        r = httpx.get(f"{host}/api/tags", timeout=3)
        if r.status_code == 200:
            data = r.json()
            return True, [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        pass
    return False, []


def run_setup(force: bool = False):
    """Run the interactive setup wizard. Safe to call anytime.

    force=False and not first run -> still runs (used by /setup); callers decide.
    Never raises; on any problem it leaves a working local-first default.
    """
    c = state.console
    cfg = state.config
    try:
        c.print("\n[bold cyan]=== Chronos Setup ===[/bold cyan]")
        c.print("[dim]Press Enter at any prompt to accept the default. Ctrl+C to skip.[/dim]\n")

        # --- Detection ---
        ollama_host = cfg.get("ollama_host", "http://localhost:11434")
        gpu = _detect_gpu()
        ollama_up, ollama_models = _ollama_status(ollama_host)

        c.print("  [bold]Detected:[/bold]")
        c.print(f"    GPU: {gpu}")
        c.print(f"    Ollama: {'running' if ollama_up else 'not detected'}"
                + (f" ({len(ollama_models)} models)" if ollama_up else ""))

        # --- Choose engine ---
        default_hint = "1" if ollama_up else "3"
        c.print("\n  [bold]How do you want to use Chronos?[/bold]")
        c.print("    [yellow]1[/yellow]. Local — Ollama (private, free)" + ("  [green](recommended)[/green]" if ollama_up else ""))
        c.print("    [yellow]2[/yellow]. Local — llama.cpp (advanced GPU control, GGUF)")
        c.print("    [yellow]3[/yellow]. Cloud API (Gemini / OpenAI / Groq / …)")
        c.print("    [yellow]4[/yellow]. AI gateway (OpenAI-compatible, e.g. OmniRoute)")
        choice = input(f"\n  Choice [{default_hint}]: ").strip() or default_hint

        if choice == "1":
            cfg.set("provider", "ollama")
            cfg.set("ollama_host", ollama_host)
            if ollama_models:
                c.print("\n  Available Ollama models:")
                for i, m in enumerate(ollama_models, 1):
                    c.print(f"    [yellow]{i}[/yellow]. {m}")
                sel = input(f"  Pick a model [1]: ").strip() or "1"
                if sel.isdigit() and 1 <= int(sel) <= len(ollama_models):
                    cfg.set("model", ollama_models[int(sel) - 1])
            else:
                c.print("\n  [yellow]No Ollama models found.[/yellow] Install one, e.g.:  ollama pull qwen3:8b")
                cfg.set("model", "")
            c.print(f"\n  [green]Set up: Ollama @ {ollama_host}[/green]")

        elif choice == "2":
            cfg.set("provider", "llamacpp")
            host = input("  llama.cpp server host [http://localhost:8080]: ").strip() or "http://localhost:8080"
            cfg.set("llamacpp_host", host)
            binp = input("  Path to llama-server binary (Enter to set later): ").strip()
            if binp:
                cfg.set("local_server_bin", binp)
            c.print(f"\n  [green]Set up: llama.cpp @ {host}[/green]")
            c.print("  [dim]Start your server with a GGUF model, then chat. (Vulkan/ROCm optional.)[/dim]")

        elif choice == "3":
            # Reuse the tested /add_provider wizard for the cloud path.
            c.print("\n  [dim]Launching the provider wizard…[/dim]")
            from cli.commands import handle_command
            handle_command("/add_provider")

        elif choice == "4":
            cfg.set("provider", "omniroute")
            url = input("  Gateway base URL [http://localhost:20128/v1]: ").strip() or "http://localhost:20128/v1"
            model = input("  Default model [auto]: ").strip() or "auto"
            env_key = "OMNIROUTE_API_KEY"
            key = input(f"  API key for {env_key} (Enter if keyless): ").strip()
            import json
            prov_file = cfg.dir / "providers.json"
            data = json.load(open(prov_file, encoding="utf-8")) if prov_file.exists() else []
            data = [p for p in data if p.get("name") != "omniroute"]
            data.append({"name": "omniroute", "type": "openai_compatible",
                         "base_url": url, "model": model, "env_key": env_key})
            json.dump(data, open(prov_file, "w", encoding="utf-8"), indent=2)
            if key:
                env_file = cfg.dir / ".env"
                existing = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
                lines = [l for l in existing.splitlines() if not l.startswith(f"{env_key}=")]
                lines.append(f"{env_key}={key}")
                env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
                os.environ[env_key] = key
            cfg.set("model", model)
            c.print(f"\n  [green]Set up: gateway @ {url}[/green]")
        else:
            c.print("  [dim]Unrecognized choice — keeping local-first Ollama default.[/dim]")
            cfg.set("provider", "ollama")

        c.print("\n  [bold green]Setup complete.[/bold green]")
        c.print("  [dim]This is your PRIMARY engine (used on startup). You can add more anytime — local or cloud — and switch instantly with /provider.[/dim]")
        c.print("  [dim]  /add_provider  — add a cloud provider (auto-discovers models)[/dim]")
        c.print("  [dim]  /provider <name>  — switch engine/provider   ·   /providers  — list all[/dim]")
        c.print("  [bold green]Type your first message, or /help.[/bold green]\n")
    except (KeyboardInterrupt, EOFError):
        # User skipped — ensure a safe local-first default exists so startup never breaks.
        c.print("\n  [dim]Setup skipped — using local-first defaults (Ollama). Re-run anytime with /setup.[/dim]\n")
        if not cfg.get("provider"):
            cfg.set("provider", "ollama")
    except Exception as e:
        c.print(f"\n  [yellow]Setup could not complete ({e}); using defaults. Try /setup later.[/yellow]\n")
