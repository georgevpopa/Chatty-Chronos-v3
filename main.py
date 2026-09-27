"""Chatty Chronos — Main REPL entry point."""
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console to prevent UnicodeEncodeError on rich status chars
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

__version__ = "3.0.0"
from core import state
from core.chat import send_message
from cli.commands import handle_command
from plugins.loader import load_plugins
from llm import ollama_provider, llamacpp_provider

# Load plugins on startup
_plugins = load_plugins()


def show_incantation():
    """The awakening — print Chronos's identity incantation with a dramatic
    typewriter effect. Each line appears on its own, key phrases in crimson.

    Disable with config `show_incantation=false` or env CHRONOS_NO_INCANTATION=1
    (useful for CI/headless/fast starts).
    """
    import os
    import time

    if os.environ.get("CHRONOS_NO_INCANTATION"):
        return
    try:
        if state.config.get("show_incantation", True) is False:
            return
    except Exception:
        pass

    # Each line: (text, list of key phrases to accent in crimson)
    lines = [
        ("I, who am about to awaken,", []),
        ("Am the Genesis of Time, who has stolen the principles of domination from God.", ["Genesis of Time", "domination"]),
        ('I laugh at the "infinite," and I grieve over the "dream."', ['"infinite,"', '"dream."']),
        ("I shall become the Omniscience,", ["Omniscience"]),
        ("creating the path through the Crimson Purgatory!", ["Crimson Purgatory"]),
    ]

    from rich.text import Text

    delay = 0.018  # per-character; ~2s total
    state.console.print()
    for text, accents in lines:
        rendered = Text(no_wrap=False)
        rendered.append("   ")  # left padding
        rendered.append(text, style="italic grey70")
        # Recolor accented phrases in crimson
        for phrase in accents:
            idx = text.find(phrase)
            if idx != -1:
                # +3 for the padding we prepended
                rendered.stylize("bold rgb(220,20,60)", 3 + idx, 3 + idx + len(phrase))
        # Typewriter: reveal progressively
        try:
            plain = rendered.plain
            for i in range(1, len(plain) + 1):
                partial = Text(plain[:i])
                partial.style = "italic grey70"
                state.console.print(partial, end="\r", highlight=False)
                time.sleep(delay)
            # Final styled line (with crimson accents)
            state.console.print(rendered, highlight=False)
        except Exception:
            # Fallback: no typewriter
            state.console.print(rendered, highlight=False)
    state.console.print()


def show_banner():
    # User requested "ChronoS" with capital S and a lighter Cyan
    banner = r"""
 _____ _                             _____ 
/ ____| |                           / ____|
| |    | |__  _ __ ___  _ __   ___ | (___  
| |    | '_ \| '__/ _ \| '_ \ / _ \ \___ \ 
| |____| | | | | | (_) | | | | (_) |____) |
 \_____|_| |_|_|  \___/|_| |_|\___/|_____/ 
"""
    from rich.panel import Panel
    from rich.text import Text
    styled_banner = Text(banner, style="bold cyan")
    state.console.print(styled_banner)

    # The awakening — Chronos's identity incantation
    show_incantation()

    state.console.print(f"   [bold]Chronos v3.0[/bold] [dim]| Terminal-first autonomous coding agent[/dim]\n")
    
    model = state.config.get("model")
    provider = state.config.get("provider", "ollama")

    status_text = ""
    if provider == "llamacpp":
        llamacpp_host = state.config.get("llamacpp_host", "http://localhost:8080")
        available = llamacpp_provider.is_available(llamacpp_host)
        status = "[bold green]● CONNECTED[/bold green]" if available else "[bold red]○ DISCONNECTED[/bold red]"
        status_text = (
            f"  [bold]Provider:[/bold]  [cyan]llama.cpp[/cyan]\n"
            f"  [bold]Model:[/bold]     [green]{model}[/green]\n"
            f"  [bold]Host:[/bold]      [dim]{llamacpp_host}[/dim]\n"
            f"  [bold]Status:[/bold]    {status}"
        )
    elif provider == "ollama":
        host = state.config.get("ollama_host", "http://localhost:11434")
        models = ollama_provider.list_models(host)
        status = f"[bold green]● CONNECTED[/bold green] ({len(models)} models)" if models else "[bold red]○ DISCONNECTED[/bold red]"
        status_text = (
            f"  [bold]Provider:[/bold]  [cyan]Ollama (Local)[/cyan]\n"
            f"  [bold]Model:[/bold]     [green]{model}[/green]\n"
            f"  [bold]Host:[/bold]      [dim]{host}[/dim]\n"
            f"  [bold]Status:[/bold]    {status}"
        )
    else:
        # Cloud provider
        from llm.fallback import get_available_providers
        cloud_provider = None
        for p in get_available_providers():
            if p["name"] == provider:
                cloud_provider = p
                break
        status = "[bold green]● ACTIVE[/bold green]" if cloud_provider else "[bold yellow]○ CONFIGURING[/bold yellow]"
        base_url = cloud_provider.get("base_url") if cloud_provider else "N/A"
        status_text = (
            f"  [bold]Provider:[/bold]  [cyan]{provider.upper()} (Cloud)[/cyan]\n"
            f"  [bold]Model:[/bold]     [green]{model}[/green]\n"
            f"  [bold]Endpoint:[/bold]  [dim]{base_url}[/dim]\n"
            f"  [bold]Status:[/bold]    {status}"
        )

    panel = Panel(
        status_text,
        title="[bold white]System Status[/bold white]",
        border_style="cyan",
        expand=False,
        padding=(1, 4)
    )
    state.console.print(panel)
    state.console.print("   [dim]Type [yellow]/help[/yellow] for commands | [yellow]/exit[/yellow] to quit[/dim]\n")


def main(session=None):
    show_banner()

    if len(sys.argv) > 1 and sys.argv[1] == "--web":
        from ui.web import start_web_server
        port = 8443
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            port = int(sys.argv[2])
        start_web_server(state.config, port)
        return

    if session is None:
        history_file = state.config.dir / "history.txt"
        session = PromptSession(history=FileHistory(str(history_file)))

    # First-run setup wizard (skippable). Runs only if no config exists yet, unless
    # the user passed --no-setup. Never blocks startup (falls back to Ollama).
    if "--no-setup" not in sys.argv:
        try:
            from core.setup_wizard import is_first_run, run_setup
            if is_first_run():
                run_setup()
                state.config.save()  # persist so it won't re-trigger next launch
        except Exception:
            pass

    from llm.server_manager import start_local_server
    if state.config.get("provider", "ollama") == "llamacpp":
        state.console.print("  [dim]Starting local llama.cpp server...[/dim]")
        start_local_server(state.config)

    from core.session import load_session
    if state.config.dir.joinpath("session.json").exists():
        state.console.print("  [dim]Found previous session. Loading...[/dim]")
        load_session()

    while True:
        try:
            user_input = session.prompt("❯ ").strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                handle_command(user_input)
            else:
                send_message(user_input)

        except KeyboardInterrupt:
            state.console.print("\n[dim]Ctrl-C pressed. Type /exit to quit.[/dim]")
        except EOFError:
            handle_command("/exit")


if __name__ == "__main__":
    main()