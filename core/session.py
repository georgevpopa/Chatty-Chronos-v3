import json
import time
from core import state
from core.logger import log

def save_session(session_id=None):
    """Save conversation to session file (supports multiple sessions)."""
    sid = session_id or state.active_session_id or str(int(time.time()))
    if not session_id and not state.active_session_id:
        state.active_session_id = sid
    
    # Save to standard session.json for CLI
    path = state.config.dir / "session.json"
    with state.messages_lock:
        data = [m for m in state.messages if m["role"] != "system"]
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        # Save to sessions folder for multi-session support
        sessions_dir = state.config.dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        session_path = sessions_dir / f"session_{sid}.json"
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error saving session: {e}", exc_info=True)


def load_session(session_id=None):
    """Load session from file (supports multiple sessions by ID)."""
    if not session_id:
        # Fallback to standard CLI session.json
        path = state.config.dir / "session.json"
        state.active_session_id = None
    else:
        path = state.config.dir / "sessions" / f"session_{session_id}.json"
        state.active_session_id = session_id
        
    if not path.exists():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        with state.messages_lock:
            state.messages.clear()
            state.messages.append({"role": "system", "content": state.SYSTEM_PROMPT})
            state.messages.extend(data)
        return True
    except Exception as e:
        log.error(f"Error loading session: {e}", exc_info=True)
        return False


def list_sessions():
    """List all available sessions."""
    sessions_dir = state.config.dir / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    results = []
    
    default_session_path = state.config.dir / "session.json"
    if default_session_path.exists():
        try:
            with open(default_session_path, "r", encoding="utf-8") as f:
                msgs = json.load(f)
            if msgs:
                first_msg = next((m["content"] for m in msgs if m["role"] == "user"), "Empty Chat")
                results.append({
                    "id": "default",
                    "title": first_msg[:30] + ("..." if len(first_msg) > 30 else ""),
                    "mtime": default_session_path.stat().st_mtime
                })
        except Exception:
            pass
            
    for f in sessions_dir.glob("session_*.json"):
        try:
            sid = f.name.replace("session_", "").replace(".json", "")
            with open(f, "r", encoding="utf-8") as file:
                msgs = json.load(file)
            first_msg = next((m["content"] for m in msgs if m["role"] == "user"), "Empty Chat")
            results.append({
                "id": sid,
                "title": first_msg[:30] + ("..." if len(first_msg) > 30 else ""),
                "mtime": f.stat().st_mtime
            })
        except Exception:
            continue
            
    # Sort by mtime descending
    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results
