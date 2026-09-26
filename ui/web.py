"""Web UI server for Chatty Chronos — serves a premium dashboard interface."""
import json
import webbrowser
import threading
import socketserver
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from rich.console import Console
import sys

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
from core.config import Config
from tools.registry import get_all_tools
from llm import ollama_provider, llamacpp_provider
from llm.fallback import get_available_providers
from plugins.loader import reload_plugins, get_loaded_plugins

console = Console()

# HTML, CSS, JS dashboard template
# Load index.html dynamically from packaged static folder
STATIC_DIR = Path(__file__).parent.parent / "static"
index_path = STATIC_DIR / "index.html"
if index_path.exists():
    INDEX_HTML = index_path.read_text(encoding="utf-8")
else:
    INDEX_HTML = "<h1>Chronos Web UI static file not found at " + str(index_path) + "</h1>"

def get_workspace_tree(root_dir):
    import os
    from pathlib import Path
    
    tree = []
    exclude_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".gemini", "vectordb"}
    exclude_exts = {".pyc", ".db", ".png", ".jpg", ".jpeg", ".webp", ".pdf", ".zip", ".gz"}
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip excluded directories in-place to prevent scanning them recursively
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == ".":
            rel_dir = ""
            
        for d in dirnames:
            tree.append({
                "path": os.path.join(rel_dir, d).replace("\\", "/"),
                "name": d,
                "type": "directory"
            })
            
        for f in filenames:
            if any(f.endswith(ext) for ext in exclude_exts):
                continue
            tree.append({
                "path": os.path.join(rel_dir, f).replace("\\", "/"),
                "name": f,
                "type": "file"
            })
            
    tree.sort(key=lambda x: (x["type"] != "directory", x["path"].lower()))
    return tree


class ChronosWebHandler(BaseHTTPRequestHandler):
    config = Config()

    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to keep console clean
        pass

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(INDEX_HTML.encode('utf-8'))
            
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            provider = self.config.get("provider", "ollama")
            model = self.config.get("model", "")
            from core.permissions import get_auto_approve_override
            auto_approve = get_auto_approve_override()
            compaction = self.config.get("compaction_enabled", True)
            self_reflection = self.config.get("self_reflection", False)
            
            # Check availability
            connected = False
            if provider == "llamacpp":
                host = self.config.get("llamacpp_host", "http://localhost:8080")
                connected = llamacpp_provider.is_available(host)
            elif provider == "ollama":
                host = self.config.get("ollama_host", "http://localhost:11434")
                connected = len(ollama_provider.list_models(host)) > 0
            else:
                connected = True  # Cloud assumed active
                
            from llm.server_manager import get_system_telemetry
            telemetry = get_system_telemetry()
            
            status_data = {
                "provider": provider,
                "model": model,
                "auto_approve_tools": auto_approve,
                "compaction_enabled": compaction,
                "self_reflection": self_reflection,
                "connected": connected,
                "telemetry": telemetry
            }
            self.wfile.write(json.dumps(status_data).encode('utf-8'))
            
        elif self.path == '/api/tools':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            tools_data = []
            for t in get_all_tools():
                tools_data.append({
                    "name": t.name,
                    "requires_permission": t.requires_permission,
                    "description": t.description
                })
            self.wfile.write(json.dumps(tools_data).encode('utf-8'))
            
        elif self.path == '/api/sessions':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            from core.session import list_sessions
            self.wfile.write(json.dumps(list_sessions()).encode('utf-8'))
            
        elif self.path == '/api/workspace/tree':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            import os
            tree = get_workspace_tree(os.getcwd())
            self.wfile.write(json.dumps(tree).encode('utf-8'))
            
        elif self.path.startswith('/api/workspace/file'):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            file_path_rel = params.get("path", [None])[0]
            
            if not file_path_rel:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing path parameter")
                return
                
            import os
            safe_root = Path(os.getcwd()).resolve()
            target_path = Path(safe_root / file_path_rel).resolve()
            
            if not str(target_path).startswith(str(safe_root)):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Access Denied")
                return
                
            if not target_path.exists() or not target_path.is_file():
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found")
                return
                
            try:
                content = target_path.read_text(encoding="utf-8", errors="replace")
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
                
        elif self.path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            def tail_file(path, n=50):
                try:
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    return [l.rstrip('\n') for l in lines[-n:]]
                except FileNotFoundError:
                    return []
                except Exception as e:
                    return [f"Error reading log: {e}"]
            
            import os
            cwd = Path(os.getcwd())
            chronos_log = cwd / 'chronos.log'
            server_log  = cwd / 'llama_server.log'
            
            log_data = {
                "chronos": tail_file(chronos_log),
                "server":  tail_file(server_log)
            }
            self.wfile.write(json.dumps(log_data).encode('utf-8'))

        elif self.path == '/api/git/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            import subprocess
            import os
            try:
                # Check if it's a git repo
                subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=os.getcwd(), capture_output=True, check=True)
                
                # Get status
                res = subprocess.run(["git", "status", "--short"], cwd=os.getcwd(), capture_output=True, text=True)
                status_lines = res.stdout.strip().split("\n") if res.stdout.strip() else []
                files = []
                for line in status_lines:
                    if len(line) >= 3:
                        state = line[:2]
                        path = line[3:]
                        files.append({"state": state, "path": path})
                
                self.wfile.write(json.dumps({"is_repo": True, "files": files}).encode('utf-8'))
            except subprocess.CalledProcessError:
                self.wfile.write(json.dumps({"is_repo": False, "files": []}).encode('utf-8'))
            except FileNotFoundError:
                self.wfile.write(json.dumps({"is_repo": False, "error": "Git not installed"}).encode('utf-8'))

        elif self.path == '/api/traces':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            try:
                from core.telemetry import get_traces_data
                traces = get_traces_data()
                self.wfile.write(json.dumps(traces).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        if self.path == '/api/chat/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            
            try:
                data = json.loads(post_data)
                prompt = data.get("message", "")
                
                from core.permissions import thread_local
                def yield_event(event):
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode('utf-8'))
                    self.wfile.flush()
                thread_local.yield_func = yield_event

                from core.chat import send_message_stream
                for event in send_message_stream(prompt):
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode('utf-8'))
                    self.wfile.flush()
            except Exception as e:
                err_event = {"type": "error", "content": str(e)}
                self.wfile.write(f"data: {json.dumps(err_event)}\n\n".encode('utf-8'))
                self.wfile.flush()
            return

        elif self.path == '/api/chat':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                data = json.loads(post_data)
                prompt = data.get("message", "")
                
                from core.chat import send_message
                from core import state
                send_message(prompt)
                
                last_assistant_msg = ""
                with state.messages_lock:
                    messages_copy = list(state.messages)
                    for m in reversed(state.messages):
                        if m["role"] == "assistant" and m.get("content"):
                            last_assistant_msg = m["content"]
                            break
                
                res_data = {
                    "status": "success",
                    "response": last_assistant_msg,
                    "messages": messages_copy
                }
            except Exception as e:
                res_data = {
                    "status": "error",
                    "error": str(e)
                }
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                data = json.loads(post_data)
                key = data.get("key")
                value = data.get("value")
                
                # Coerce types
                if value == "true" or value is True:
                    value = True
                elif value == "false" or value is False:
                    value = False
                
                if key == "auto_approve_tools":
                    from core.permissions import set_auto_approve_override
                    set_auto_approve_override(value)
                else:
                    self.config.set(key, value)
                res_data = {"status": "success"}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/git/suggest':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            try:
                import subprocess
                import os
                
                # Get the diff
                diff_res = subprocess.run(["git", "diff", "--cached"], cwd=os.getcwd(), capture_output=True, text=True)
                diff = diff_res.stdout
                if not diff:
                    diff_res = subprocess.run(["git", "diff"], cwd=os.getcwd(), capture_output=True, text=True)
                    diff = diff_res.stdout
                
                if not diff.strip():
                    self.wfile.write(json.dumps({"status": "error", "error": "No changes to commit."}).encode('utf-8'))
                    return
                
                # Truncate diff if too large
                if len(diff) > 8000:
                    diff = diff[:8000] + "\n... (diff truncated)"
                    
                prompt = (
                    "Write a concise, professional Git commit message for the following diff. "
                    "Use the conventional commits format (e.g. feat: ..., fix: ..., docs: ...). "
                    "Return ONLY the commit message text, nothing else.\n\n"
                    f"{diff}"
                )
                
                from core.agent import ReActAgent
                agent = ReActAgent(self.config, max_iterations=2) # Very small loop
                
                # We can just call the LLM directly to be faster, bypassing the ReAct loop
                from llm.fallback import generate_chat_response
                tmp_msgs = [{"role": "system", "content": "You are an expert developer."}, {"role": "user", "content": prompt}]
                msg = generate_chat_response(tmp_msgs, self.config)
                
                res_data = {"status": "success", "message": msg.strip().replace('"', '').replace('`', '')}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/git/commit':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            try:
                data = json.loads(post_data)
                message = data.get("message", "Auto-commit")
                import subprocess
                import os
                
                # Add all
                subprocess.run(["git", "add", "-A"], cwd=os.getcwd(), check=True)
                # Commit
                subprocess.run(["git", "commit", "-m", message], cwd=os.getcwd(), capture_output=True, check=True)
                
                res_data = {"status": "success"}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/plugins/reload':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            count = reload_plugins()
            plugins = [p.name for p in get_loaded_plugins()]
            self.wfile.write(json.dumps({"status": "success", "count": count, "plugins": plugins}).encode('utf-8'))
            
        elif self.path == '/api/mcp/list':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            try:
                from pathlib import Path
                mcp_conf = Path.home() / ".chatty-chronos" / "mcp_servers.json"
                if mcp_conf.exists():
                    with open(mcp_conf, "r") as f:
                        servers = json.load(f)
                else:
                    servers = {
                        "github": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"]},
                        "sqlite": {"command": "uvx", "args": ["mcp-server-sqlite", "--db-path", "memory.db"]},
                        "postgres": {"command": "uvx", "args": ["mcp-server-postgres", "postgresql://localhost/test"]},
                        "git": {"command": "uvx", "args": ["mcp-server-git"]}
                    }
                    mcp_conf.parent.mkdir(exist_ok=True, parents=True)
                    with open(mcp_conf, "w") as f:
                        json.dump(servers, f, indent=2)
                        
                from core.mcp_client import get_mcp_manager
                manager = get_mcp_manager()
                
                res_servers = []
                for name, cfg in servers.items():
                    res_servers.append({
                        "name": name,
                        "command": cfg.get("command"),
                        "args": cfg.get("args", []),
                        "connected": name in manager.servers
                    })
                res_data = {"status": "success", "servers": res_servers}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/mcp/connect':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            try:
                data = json.loads(post_data)
                name = data.get("name")
                
                from pathlib import Path
                mcp_conf = Path.home() / ".chatty-chronos" / "mcp_servers.json"
                if mcp_conf.exists():
                    with open(mcp_conf, "r") as f:
                        servers = json.load(f)
                else:
                    servers = {}
                    
                if name not in servers:
                    raise Exception(f"Server {name} not configured.")
                    
                cfg = servers[name]
                command = cfg.get("command")
                args = cfg.get("args", [])
                
                from core.mcp_client import get_mcp_manager
                manager = get_mcp_manager()
                
                import asyncio
                success = asyncio.run(manager.connect(name, command, args))
                
                if success:
                    from tools.mcp_tool import MCPToolWrapper
                    from tools.registry import register_tool
                    tools = manager.get_server_tools(name)
                    for t in tools:
                        wrapped = MCPToolWrapper(name, t)
                        register_tool(wrapped)
                    res_data = {"status": "success", "tools_count": len(tools)}
                else:
                    res_data = {"status": "error", "error": "Failed to connect to MCP server"}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/clear':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            from core import state
            with state.messages_lock:
                state.messages.clear()
                state.messages.append({"role": "system", "content": state.SYSTEM_PROMPT})
            from core.permissions import reset_session_trust
            reset_session_trust()
            
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            
        elif self.path == '/api/chat/permission':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                data = json.loads(post_data)
                req_id = data.get("req_id")
                choice = data.get("choice")
                
                from core.permissions import _pending_permissions, _pending_permissions_lock
                
                with _pending_permissions_lock:
                    req = _pending_permissions.get(req_id)
                if req:
                    req["response"] = choice
                    req["event"].set()
                    res_data = {"status": "success"}
                else:
                    res_data = {"status": "error", "error": "Request ID not found or already resolved"}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/chat/prompt':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                data = json.loads(post_data)
                req_id = data.get("req_id")
                answer = data.get("answer")
                
                from core.permissions import _pending_prompts, _pending_prompts_lock
                
                with _pending_prompts_lock:
                    req = _pending_prompts.get(req_id)
                if req:
                    req["response"] = answer
                    req["event"].set()
                    res_data = {"status": "success"}
                else:
                    res_data = {"status": "error", "error": "Request ID not found or already resolved"}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/server/restart':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                from llm.server_manager import stop_local_server, start_local_server
                stop_local_server()
                start_local_server(self.config)
                res_data = {"status": "success"}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        elif self.path == '/api/sessions/create':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            from core import state
            import time
            with state.messages_lock:
                state.messages.clear()
                state.messages.append({"role": "system", "content": state.SYSTEM_PROMPT})
                state.active_session_id = str(int(time.time()))
            from core.permissions import reset_session_trust
            reset_session_trust()
            self.wfile.write(json.dumps({"status": "success", "id": state.active_session_id}).encode('utf-8'))

        elif self.path == '/api/sessions/load':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                data = json.loads(post_data)
                sid = data.get("id")
                from core.session import load_session
                from core import state
                success = load_session(sid)
                with state.messages_lock:
                    messages_copy = list(state.messages)
                if success:
                    res_data = {"status": "success", "messages": messages_copy}
                else:
                    res_data = {"status": "error", "error": "Session not found"}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))

        elif self.path == '/api/sessions/delete':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            try:
                data = json.loads(post_data)
                sid = data.get("id")
                if sid == "default":
                    path = self.config.dir / "session.json"
                else:
                    path = self.config.dir / "sessions" / f"session_{sid}.json"
                if path.exists():
                    import os
                    os.remove(path)
                    res_data = {"status": "success"}
                else:
                    res_data = {"status": "error", "error": "File not found"}
            except Exception as e:
                res_data = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(res_data).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()


def start_web_server(config: Config, port: int = 8443):
    """Starts the Web interface HTTP server in a background thread. Auto-scans for open ports."""
    from core.permissions import set_web_mode_active
    set_web_mode_active(True)
    
    httpd = None
    active_port = port
    for p in range(port, port + 10):
        try:
            server_address = ('', p)
            httpd = ThreadingHTTPServer(server_address, ChronosWebHandler)
            active_port = p
            break
        except OSError:
            continue
            
    if not httpd:
        console.print(f"  [red]FAIL: Could not bind Web UI server to any port in range {port}-{port+9}[/red]")
        return
        
    url = f"http://localhost:{active_port}"
    console.print(f"\n[bold green]🚀 Chronos Web UI launched successfully![/bold green]")
    console.print(f"   Dashboard URL: [cyan]{url}[/cyan]")
    console.print(f"   [dim]Interactive tool permission prompts are active.[/dim]\n")
    
    # Run server in thread
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    
    # Auto-open browser
    webbrowser.open(url)
    
if __name__ == '__main__':
    from core.config import Config
    import time
    config = Config()
    start_web_server(config, 8443)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
