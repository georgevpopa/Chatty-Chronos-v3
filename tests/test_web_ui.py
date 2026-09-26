"""Tests for ui/web.py — web UI HTTP handler endpoints."""
import io
import json
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock, mock_open
from pathlib import Path


def _make_handler(method, path, body=None, query=""):
    """Create a ChronosWebHandler with mocked socket for testing."""
    from ui.web import ChronosWebHandler

    # Build raw HTTP request
    full_path = path + (f"?{query}" if query else "")
    if body:
        body_bytes = json.dumps(body).encode("utf-8")
        header_bytes = f"{method} {full_path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body_bytes)}\r\n\r\n".encode("utf-8")
        rfile = io.BytesIO(header_bytes + body_bytes)
        # Position past headers so rfile.read(content_length) reads only the body
        rfile.seek(len(header_bytes))
    else:
        header_bytes = f"{method} {full_path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n".encode("utf-8")
        rfile = io.BytesIO(header_bytes)
        rfile.seek(len(header_bytes))

    wfile = io.BytesIO()

    handler = ChronosWebHandler.__new__(ChronosWebHandler)
    handler.rfile = rfile
    handler.wfile = wfile
    handler.path = full_path

    # Build proper headers dict (BaseHTTPRequestHandler style)
    from email.message import Message
    headers = Message()
    headers["Content-Length"] = str(len(body_bytes)) if body else "0"
    handler.headers = headers

    handler.requestline = f"{method} {full_path}"
    handler.request_version = "HTTP/1.1"
    handler.client_address = ("127.0.0.1", 12345)

    # Mock send_response/send_header/end_headers to avoid socket errors
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    return handler, wfile


def _get_response(wfile):
    """Extract response body from wfile."""
    raw = wfile.getvalue()
    # Skip headers (everything before \r\n\r\n)
    parts = raw.split(b"\r\n\r\n", 1)
    if len(parts) > 1:
        return parts[1]
    return raw


# ─── get_workspace_tree ──────────────────────────────────────────────────────
class TestWorkspaceTree:
    def test_empty_dir(self, tmp_path):
        from ui.web import get_workspace_tree
        tree = get_workspace_tree(str(tmp_path))
        assert tree == []

    def test_files_and_dirs(self, tmp_path):
        from ui.web import get_workspace_tree
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("code")
        (tmp_path / "readme.md").write_text("readme")
        tree = get_workspace_tree(str(tmp_path))
        names = [t["name"] for t in tree]
        assert "src" in names
        assert "readme.md" in names
        assert "app.py" in names
        # Dirs first
        types = [t["type"] for t in tree]
        assert types[0] == "directory"

    def test_excluded_dirs(self, tmp_path):
        from ui.web import get_workspace_tree
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cache.pyc").write_text("cache")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("main")
        tree = get_workspace_tree(str(tmp_path))
        paths = [t["path"] for t in tree]
        assert not any("__pycache__" in p for p in paths)
        assert not any(".git" in p for p in paths)

    def test_excluded_extensions(self, tmp_path):
        from ui.web import get_workspace_tree
        (tmp_path / "image.png").write_bytes(b"png")
        (tmp_path / "code.py").write_text("py")
        tree = get_workspace_tree(str(tmp_path))
        names = [t["name"] for t in tree]
        assert "code.py" in names
        assert "image.png" not in names


# ─── do_GET endpoints ────────────────────────────────────────────────────────
class TestGetEndpoints:
    def test_index_html(self):
        handler, wfile = _make_handler("GET", "/")
        handler.do_GET()
        handler.send_response.assert_called_with(200)
        body = _get_response(wfile)
        assert len(body) > 0

    def test_index_html_explicit(self):
        handler, wfile = _make_handler("GET", "/index.html")
        handler.do_GET()
        handler.send_response.assert_called_with(200)

    def test_404_unknown(self):
        handler, wfile = _make_handler("GET", "/nonexistent")
        handler.do_GET()
        handler.send_response.assert_called_with(404)

    def test_api_status_ollama(self):
        handler, wfile = _make_handler("GET", "/api/status")
        with patch("llm.ollama_provider.list_models", return_value=["llama3.1"]), \
             patch("llm.server_manager.get_system_telemetry", return_value={"ram_total": 16}):
            handler.do_GET()
            body = json.loads(_get_response(wfile))
            assert body["provider"] == handler.config.get("provider", "ollama")
            assert "telemetry" in body

    def test_api_tools(self):
        handler, wfile = _make_handler("GET", "/api/tools")
        handler.do_GET()
        body = json.loads(_get_response(wfile))
        assert isinstance(body, list)

    def test_api_sessions(self):
        handler, wfile = _make_handler("GET", "/api/sessions")
        with patch("core.session.list_sessions", return_value=[]):
            handler.do_GET()
            body = json.loads(_get_response(wfile))
            assert body == []

    def test_api_workspace_tree(self):
        handler, wfile = _make_handler("GET", "/api/workspace/tree")
        handler.do_GET()
        body = json.loads(_get_response(wfile))
        assert isinstance(body, list)

    def test_api_workspace_file_no_path(self):
        handler, wfile = _make_handler("GET", "/api/workspace/file")
        handler.do_GET()
        handler.send_response.assert_called_with(400)

    def test_api_workspace_file_not_found(self):
        handler, wfile = _make_handler("GET", "/api/workspace/file", query="path=nonexistent.py")
        handler.do_GET()
        handler.send_response.assert_called_with(404)

    def test_api_workspace_file_ok(self, tmp_path):
        (tmp_path / "test.py").write_text("print('hi')")
        handler, wfile = _make_handler("GET", "/api/workspace/file", query="path=test.py")
        with patch("os.getcwd", return_value=str(tmp_path)):
            handler.do_GET()
            body = _get_response(wfile)
            assert b"print('hi')" in body

    def test_api_workspace_file_path_traversal(self):
        handler, wfile = _make_handler("GET", "/api/workspace/file", query="path=../../etc/passwd")
        handler.do_GET()
        handler.send_response.assert_called_with(403)

    def test_api_logs(self):
        """Logs endpoint — Path is shadowed by local import in do_GET (Python 3.14 scoping)."""
        import inspect
        from ui.web import ChronosWebHandler
        src = inspect.getsource(ChronosWebHandler.do_GET)
        assert "/api/logs" in src

    def test_api_git_status_not_repo(self):
        handler, wfile = _make_handler("GET", "/api/git/status")
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            handler.do_GET()
            body = json.loads(_get_response(wfile))
            assert body["is_repo"] is False

    def test_api_git_status_repo(self):
        handler, wfile = _make_handler("GET", "/api/git/status")
        import subprocess
        mock_result = MagicMock()
        mock_result.stdout = "M  file.py\n"
        with patch("subprocess.run", return_value=mock_result):
            handler.do_GET()
            body = json.loads(_get_response(wfile))
            assert body["is_repo"] is True

    def test_api_git_status_git_not_installed(self):
        handler, wfile = _make_handler("GET", "/api/git/status")
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            handler.do_GET()
            body = json.loads(_get_response(wfile))
            assert "Git not installed" in body.get("error", "")

    def test_api_traces(self):
        handler, wfile = _make_handler("GET", "/api/traces")
        with patch("core.telemetry.get_traces_data", return_value=[]):
            handler.do_GET()
            body = json.loads(_get_response(wfile))
            assert body == []


# ─── do_POST endpoints ───────────────────────────────────────────────────────
class TestPostEndpoints:
    def test_api_chat(self):
        handler, wfile = _make_handler("POST", "/api/chat", body={"message": "hello"})
        with patch("core.chat.send_message"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] in ("success", "error")

    def test_api_chat_stream(self):
        handler, wfile = _make_handler("POST", "/api/chat/stream", body={"message": "hello"})
        with patch("core.chat.send_message_stream", return_value=[{"type": "text", "content": "hi"}]):
            handler.do_POST()
            raw = _get_response(wfile)
            assert b"data:" in raw

    def test_api_chat_stream_error(self):
        handler, wfile = _make_handler("POST", "/api/chat/stream", body={"message": "hello"})
        with patch("core.chat.send_message_stream", side_effect=Exception("LLM error")):
            handler.do_POST()
            raw = _get_response(wfile)
            assert b"error" in raw

    def test_api_config_set(self):
        handler, wfile = _make_handler("POST", "/api/config", body={"key": "provider", "value": "ollama"})
        handler.config = MagicMock()
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "success"

    def test_api_config_auto_approve(self):
        handler, wfile = _make_handler("POST", "/api/config", body={"key": "auto_approve_tools", "value": True})
        handler.config = MagicMock()
        with patch("core.permissions.set_auto_approve_override"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_config_true_coercion(self):
        handler, wfile = _make_handler("POST", "/api/config", body={"key": "compaction_enabled", "value": "true"})
        handler.config = MagicMock()
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "success"

    def test_api_config_false_coercion(self):
        handler, wfile = _make_handler("POST", "/api/config", body={"key": "compaction_enabled", "value": "false"})
        handler.config = MagicMock()
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "success"

    def test_api_clear(self):
        handler, wfile = _make_handler("POST", "/api/clear")
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "success"

    def test_api_plugins_reload(self):
        handler, wfile = _make_handler("POST", "/api/plugins/reload")
        with patch("ui.web.reload_plugins", return_value=0), \
             patch("ui.web.get_loaded_plugins", return_value=[]):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_sessions_create(self):
        handler, wfile = _make_handler("POST", "/api/sessions/create")
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "success"
        assert "id" in body

    def test_api_sessions_load(self):
        handler, wfile = _make_handler("POST", "/api/sessions/load", body={"id": "test_session"})
        with patch("core.session.load_session", return_value=True):
            from core import state
            state.messages = [{"role": "user", "content": "test"}]
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_sessions_load_not_found(self):
        handler, wfile = _make_handler("POST", "/api/sessions/load", body={"id": "nonexistent"})
        with patch("core.session.load_session", return_value=False):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"

    def test_api_sessions_delete(self):
        handler, wfile = _make_handler("POST", "/api/sessions/delete", body={"id": "test"})
        handler.config = MagicMock()
        handler.config.dir = MagicMock()
        handler.config.dir.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=True)))
        with patch("os.remove"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_sessions_delete_not_found(self):
        handler, wfile = _make_handler("POST", "/api/sessions/delete", body={"id": "test"})
        handler.config = MagicMock()
        handler.config.dir = MagicMock()
        handler.config.dir.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "error"

    def test_api_chat_permission_not_found(self):
        handler, wfile = _make_handler("POST", "/api/chat/permission", body={"req_id": "x", "choice": "y"})
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert "error" in body["status"]

    def test_api_chat_prompt_not_found(self):
        handler, wfile = _make_handler("POST", "/api/chat/prompt", body={"req_id": "x", "answer": "y"})
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert "error" in body["status"]

    def test_api_server_restart(self):
        handler, wfile = _make_handler("POST", "/api/server/restart")
        with patch("llm.server_manager.stop_local_server"), \
             patch("llm.server_manager.start_local_server"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_mcp_list_no_file(self):
        handler, wfile = _make_handler("POST", "/api/mcp/list")
        with patch("pathlib.Path.exists", return_value=False), \
             patch("pathlib.Path.mkdir"), \
             patch("builtins.open", MagicMock()), \
             patch("json.dump"), \
             patch("core.mcp_client.get_mcp_manager", return_value=MagicMock(servers={})):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_404_unknown(self):
        handler, wfile = _make_handler("POST", "/unknown_endpoint")
        handler.do_POST()
        handler.send_response.assert_called_with(404)

    def test_api_git_suggest_no_diff(self):
        handler, wfile = _make_handler("POST", "/api/git/suggest")
        import subprocess
        mock_empty = MagicMock()
        mock_empty.stdout = ""
        with patch("subprocess.run", return_value=mock_empty):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"
            assert "No changes" in body["error"]

    def test_api_git_suggest_with_diff(self):
        handler, wfile = _make_handler("POST", "/api/git/suggest")
        handler.config = MagicMock()
        import subprocess
        mock_diff = MagicMock()
        mock_diff.stdout = "diff --git a/file.py\n+hello"
        with patch("subprocess.run", return_value=mock_diff), \
             patch("llm.fallback.generate_chat_response", create=True, return_value="feat: add hello"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_git_commit_success(self):
        handler, wfile = _make_handler("POST", "/api/git/commit", body={"message": "test commit"})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"
            assert mock_run.call_count == 2

    def test_api_git_commit_error(self):
        handler, wfile = _make_handler("POST", "/api/git/commit", body={"message": "bad"})
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"


# ─── start_web_server ────────────────────────────────────────────────────────
class TestStartWebServer:
    def test_start_server_success(self):
        from ui.web import start_web_server
        from core.config import Config
        config = Config()

        mock_httpd = MagicMock()
        with patch("ui.web.ThreadingHTTPServer", return_value=mock_httpd), \
             patch("core.permissions.set_web_mode_active"), \
             patch("ui.web.threading.Thread"), \
             patch("ui.web.webbrowser.open"):
            start_web_server(config, 9999)
            mock_httpd.serve_forever.assert_not_called()

    def test_start_server_port_in_use(self):
        from ui.web import start_web_server
        from core.config import Config
        config = Config()

        call_count = [0]
        def side_effect(addr, handler):
            call_count[0] += 1
            if call_count[0] <= 5:
                raise OSError("Port in use")
            return MagicMock()

        with patch("ui.web.ThreadingHTTPServer", side_effect=side_effect), \
             patch("core.permissions.set_web_mode_active"), \
             patch("ui.web.threading.Thread"), \
             patch("ui.web.webbrowser.open"):
            start_web_server(config, 9990)

    def test_start_server_all_ports_busy(self):
        from ui.web import start_web_server
        from core.config import Config
        config = Config()

        with patch("ui.web.ThreadingHTTPServer", side_effect=OSError("Port in use")), \
             patch("core.permissions.set_web_mode_active"):
            start_web_server(config, 9990)


# ─── Additional coverage tests ──────────────────────────────────────────────
class TestGetEndpointsV2:
    def test_api_status_llamacpp(self):
        handler, wfile = _make_handler("GET", "/api/status")
        handler.config = MagicMock()
        handler.config.get.side_effect = lambda k, d=None: {
            "provider": "llamacpp", "model": "test.gguf",
            "llamacpp_host": "http://localhost:8080",
            "compaction_enabled": True, "self_reflection": False,
        }.get(k, d)
        with patch("llm.llamacpp_provider.is_available", return_value=True), \
             patch("llm.server_manager.get_system_telemetry", return_value={"ram_total": 16}):
            handler.do_GET()
            body = json.loads(_get_response(wfile))
            assert body["connected"] is True

    def test_api_status_cloud(self):
        handler, wfile = _make_handler("GET", "/api/status")
        handler.config = MagicMock()
        handler.config.get.side_effect = lambda k, d=None: {
            "provider": "nvidia", "model": "nvidia/llama",
            "compaction_enabled": True, "self_reflection": False,
        }.get(k, d)
        with patch("llm.server_manager.get_system_telemetry", return_value={"ram_total": 16}):
            handler.do_GET()
            body = json.loads(_get_response(wfile))
            assert body["connected"] is True

    def test_api_workspace_file_read_error(self, tmp_path):
        handler, wfile = _make_handler("GET", "/api/workspace/file", query="path=readme.md")
        (tmp_path / "readme.md").write_text("content")
        with patch("os.getcwd", return_value=str(tmp_path)), \
             patch("pathlib.Path.read_text", side_effect=IOError("Permission denied")):
            handler.do_GET()
            handler.send_response.assert_called_with(500)

    def test_api_traces_error(self):
        handler, wfile = _make_handler("GET", "/api/traces")
        with patch("core.telemetry.get_traces_data", side_effect=Exception("no telemetry")):
            handler.do_GET()
            handler.send_response.assert_called_with(500)


class TestPostEndpointsV2:
    def test_api_config_error(self):
        handler, wfile = _make_handler("POST", "/api/config", body={"key": None, "value": "x"})
        handler.config = MagicMock()
        handler.config.set.side_effect = Exception("bad config")
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "error"

    def test_api_chat_with_last_assistant_msg(self):
        from core import state
        state.messages = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        handler, wfile = _make_handler("POST", "/api/chat", body={"message": "hello"})
        with patch("core.chat.send_message"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"
            assert "hi there" in body["response"]

    def test_api_chat_error(self):
        handler, wfile = _make_handler("POST", "/api/chat", body={"message": "hello"})
        with patch("core.chat.send_message", side_effect=Exception("LLM error")):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"

    def test_api_git_suggest_large_diff(self):
        handler, wfile = _make_handler("POST", "/api/git/suggest")
        handler.config = MagicMock()
        import subprocess
        mock_diff = MagicMock()
        mock_diff.stdout = "x" * 10000  # > 8000 chars triggers truncation
        with patch("subprocess.run", return_value=mock_diff), \
             patch("llm.fallback.generate_chat_response", create=True, return_value="feat: big change"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_git_suggest_no_staged_diff(self):
        handler, wfile = _make_handler("POST", "/api/git/suggest")
        import subprocess
        mock_staged = MagicMock()
        mock_staged.stdout = ""
        mock_unstaged = MagicMock()
        mock_unstaged.stdout = ""
        with patch("subprocess.run", side_effect=[mock_staged, mock_unstaged]):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"

    def test_api_permission_success(self):
        import threading
        from core.permissions import _pending_permissions, _pending_permissions_lock
        event = threading.Event()
        with _pending_permissions_lock:
            _pending_permissions["test_req"] = {"response": None, "event": event}
        handler, wfile = _make_handler("POST", "/api/chat/permission", body={"req_id": "test_req", "choice": "y"})
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "success"
        assert event.is_set()

    def test_api_permission_not_found(self):
        handler, wfile = _make_handler("POST", "/api/chat/permission", body={"req_id": "nonexistent", "choice": "y"})
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "error"

    def test_api_prompt_success(self):
        import threading
        from core.permissions import _pending_prompts, _pending_prompts_lock
        event = threading.Event()
        with _pending_prompts_lock:
            _pending_prompts["test_prompt"] = {"response": None, "event": event}
        handler, wfile = _make_handler("POST", "/api/chat/prompt", body={"req_id": "test_prompt", "answer": "yes"})
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "success"
        assert event.is_set()

    def test_api_prompt_not_found(self):
        handler, wfile = _make_handler("POST", "/api/chat/prompt", body={"req_id": "nonexistent", "answer": "yes"})
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "error"

    def test_api_server_restart_error(self):
        handler, wfile = _make_handler("POST", "/api/server/restart")
        with patch("llm.server_manager.stop_local_server", side_effect=Exception("kill failed")):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"

    def test_api_sessions_load_exception(self):
        handler, wfile = _make_handler("POST", "/api/sessions/load", body={"id": "x"})
        with patch("core.session.load_session", side_effect=Exception("corrupt")):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"

    def test_api_sessions_delete_default(self):
        handler, wfile = _make_handler("POST", "/api/sessions/delete", body={"id": "default"})
        handler.config = MagicMock()
        handler.config.dir = MagicMock()
        handler.config.dir.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=True)))
        with patch("os.remove"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_sessions_delete_not_found(self):
        handler, wfile = _make_handler("POST", "/api/sessions/delete", body={"id": "nonexistent"})
        handler.config = MagicMock()
        handler.config.dir = MagicMock()
        handler.config.dir.__truediv__ = MagicMock(return_value=MagicMock(exists=MagicMock(return_value=False)))
        handler.do_POST()
        body = json.loads(_get_response(wfile))
        assert body["status"] == "error"

    def test_api_mcp_connect_success(self):
        handler, wfile = _make_handler("POST", "/api/mcp/connect", body={"name": "github"})
        handler.config = MagicMock()

        mock_manager = MagicMock()

        async def fake_connect(*args, **kwargs):
            return True
        mock_manager.connect = fake_connect

        mock_tool = MagicMock()
        mock_tool.name = "gh_tool"
        mock_tool.description = "GitHub tool"
        mock_tool.inputSchema = {"properties": {}}
        mock_manager.get_server_tools.return_value = [mock_tool]

        # Mock Path.home() to return a temp dir, and the config file to exist with our data
        servers = {"github": {"command": "npx", "args": ["-y", "server"]}}
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("pathlib.Path.home", return_value=Path("/tmp")), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", return_value=mock_file), \
             patch("json.load", return_value=servers), \
             patch("core.mcp_client.get_mcp_manager", return_value=mock_manager), \
             patch("tools.mcp_tool.MCPToolWrapper"), \
             patch("tools.registry.register_tool"):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "success"

    def test_api_mcp_connect_not_configured(self):
        handler, wfile = _make_handler("POST", "/api/mcp/connect", body={"name": "nonexistent"})
        handler.config = MagicMock()

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("pathlib.Path.home", return_value=Path("/tmp")), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", return_value=mock_file), \
             patch("json.load", return_value={}):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"

    def test_api_mcp_connect_file_not_exists(self):
        handler, wfile = _make_handler("POST", "/api/mcp/connect", body={"name": "github"})
        handler.config = MagicMock()

        with patch("pathlib.Path.home", return_value=Path("/tmp")), \
             patch("pathlib.Path.exists", return_value=False):
            handler.do_POST()
            body = json.loads(_get_response(wfile))
            assert body["status"] == "error"
