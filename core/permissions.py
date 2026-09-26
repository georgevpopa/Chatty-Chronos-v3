"""Permission system — 3-tier trust model.
Levels:
  y  = allow this one command
  ya = allow all commands for this task (session)
  yw = trust this workspace permanently
  n  = deny
"""
import json
import threading
from pathlib import Path
from rich.console import Console

console = Console()

# Session-level: trust all for current task
_session_trust_all = False

# Transient in-memory override for Web UI mode
_auto_approve_override = False

# Web mode and pending requests tracking
import uuid
_web_mode_active = False
_pending_permissions = {}
_pending_permissions_lock = threading.Lock()

_pending_prompts = {}
_pending_prompts_lock = threading.Lock()
thread_local = threading.local()


def set_web_mode_active(val: bool):
    global _web_mode_active
    _web_mode_active = val


def set_auto_approve_override(val: bool):
    global _auto_approve_override
    _auto_approve_override = val


def get_auto_approve_override() -> bool:
    return _auto_approve_override


# Workspace trust file
TRUST_FILE = Path.home() / ".chatty-chronos" / "trusted_workspaces"


def _load_trusted_workspaces() -> set:
    if TRUST_FILE.exists():
        return set(TRUST_FILE.read_text().strip().splitlines())
    return set()


def _save_trusted_workspace(path: str):
    workspaces = _load_trusted_workspaces()
    workspaces.add(path)
    TRUST_FILE.parent.mkdir(exist_ok=True)
    TRUST_FILE.write_text("\n".join(sorted(workspaces)) + "\n")


def is_workspace_trusted(cwd: str = None) -> bool:
    """Check if current workspace is permanently trusted."""
    if cwd is None:
        cwd = str(Path.cwd())
    trusted = _load_trusted_workspaces()
    p = Path(cwd).resolve()
    while p != p.parent:
        if str(p) in trusted:
            return True
        p = p.parent
    return str(p) in trusted


def request_permission(tool_name: str, description: str, cwd: str = None, diff_text: str = None) -> bool:
    """Ask user for permission via an interactive select menu or Web UI prompt. Returns True if allowed.
    
    Respects session trust and workspace trust.
    """
    global _session_trust_all, _auto_approve_override, _web_mode_active

    # In-memory transient override (for Web UI)
    if _auto_approve_override:
        return True

    # Session-level trust (ya was given earlier)
    if _session_trust_all:
        return True

    # Workspace-level trust
    if is_workspace_trusted(cwd):
        return True

    # Auto-approve from config
    try:
        from core.config import Config
        cfg = Config()
        if cfg.get("auto_approve_tools", False):
            return True
    except Exception:
        pass

    # If running in Web UI mode and thread_local holds the SSE yield function
    yield_func = getattr(thread_local, "yield_func", None)
    if _web_mode_active and yield_func is not None:
        req_id = str(uuid.uuid4())
        event = threading.Event()
        
        with _pending_permissions_lock:
            _pending_permissions[req_id] = {
                "tool": tool_name,
                "desc": description,
                "diff": diff_text,
                "event": event,
                "response": None
            }
            
        try:
            # Yield permission required event to browser via SSE
            yield_func({"type": "permission_required", "req_id": req_id, "tool": tool_name, "desc": description, "diff": diff_text})
        except Exception:
            return False
            
        # Block handler thread waiting for the HTTP permission POST request
        event.wait()
        
        with _pending_permissions_lock:
            req_data = _pending_permissions.pop(req_id, {})
            res = req_data.get("response")
            
        if res == "y" or res == "yes":
            return True
        elif res == "ya":
            _session_trust_all = True
            return True
        elif res == "yw":
            workspace = cwd or str(Path.cwd())
            _save_trusted_workspace(workspace)
            return True
        else:
            return False

    # Ask user
    console.print(f"\n  [yellow]⚠ Permission required:[/yellow] [bold]{tool_name}[/bold]")
    console.print(f"  [dim]{description}[/dim]")

    # Map display labels to internal action codes
    _PERMISSION_CHOICES = {
        "Yes, allow once":               "y",
        "Yes to all (for this session)":  "ya",
        "Trust this workspace permanently": "yw",
        "No, deny":                      "n",
    }
    _LABELS = list(_PERMISSION_CHOICES.keys())

    try:
        import questionary
        selected_label = questionary.select(
            "  Allow execution?",
            choices=_LABELS,
            default=_LABELS[0],
        ).ask()
        choice = _PERMISSION_CHOICES.get(selected_label, "n") if selected_label else "n"
    except (KeyboardInterrupt, EOFError, ImportError):
        # Fallback to standard input if questionary is not available
        try:
            console.print(f"  [dim][y]es / [n]o / [ya] yes-all (session) / [yw] trust workspace[/dim]")
            choice = input("  Allow? ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return False

    if choice == "y" or choice == "yes":
        return True
    elif choice == "ya":
        _session_trust_all = True
        console.print("  [green]Trusted for this session.[/green]")
        return True
    elif choice == "yw":
        workspace = cwd or str(Path.cwd())
        _save_trusted_workspace(workspace)
        console.print(f"  [green]Workspace trusted permanently: {workspace}[/green]")
        return True
    else:
        console.print("  [red]Denied.[/red]")
        return False


def reset_session_trust():
    """Reset session-level trust (call on /clear or new task)."""
    global _session_trust_all
    _session_trust_all = False


def ask_user_prompt(question: str) -> str:
    """Pause the agent and ask the user a free-text question.
    
    If in Web UI mode, triggers a modal. Otherwise, uses CLI input.
    """
    global _web_mode_active

    yield_func = getattr(thread_local, "yield_func", None)
    if _web_mode_active and yield_func is not None:
        req_id = str(uuid.uuid4())
        event = threading.Event()
        
        with _pending_prompts_lock:
            _pending_prompts[req_id] = {
                "question": question,
                "event": event,
                "response": ""
            }
            
        try:
            # Yield prompt event to browser
            yield_func({"type": "user_prompt_required", "req_id": req_id, "question": question})
        except Exception:
            return "(No response provided due to error)"
            
        # Block handler thread waiting for the HTTP POST request
        event.wait()
        
        with _pending_prompts_lock:
            req_data = _pending_prompts.pop(req_id, {})
            return req_data.get("response", "")

    # CLI fallback
    try:
        import questionary
        answer = questionary.text(f"\n  [magenta]Agent asks:[/magenta] {question}").ask()
        return answer if answer else ""
    except (KeyboardInterrupt, EOFError, ImportError):
        console.print(f"\n  [magenta]Agent asks:[/magenta] {question}")
        try:
            return input("  Your answer: ").strip()
        except (KeyboardInterrupt, EOFError):
            return ""
