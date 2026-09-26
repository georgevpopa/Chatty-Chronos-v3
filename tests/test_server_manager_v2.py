"""Extended tests for llm/server_manager.py — covering remaining uncovered paths."""
import subprocess
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


def _make_config(tmp_path, extra=None):
    """Create a mock config with all needed keys, using a real tmp_path."""
    defaults = {
        "local_server_enabled": True,
        "llamacpp_host": "http://localhost:8080",
        "local_server_model": "E:\\models\\qwen.gguf",
        "local_server_bin": "E:\\llama\\server.exe",
        "local_server_port": 8080,
        "local_server_ngl": 20,
        "local_server_ctx": 4096,
        "local_server_parallel": 1,
        "local_server_reasoning_budget": 1024,
        "local_server_cache_ram": 512,
        "local_server_env": {},
    }
    if extra:
        defaults.update(extra)

    mock_config = MagicMock()
    mock_config.get.side_effect = lambda k, d=None: defaults.get(k, d)
    mock_config.dir = tmp_path
    return mock_config


# ─── start_local_server — subprocess launch (lines 130-176) ─────────────────
class TestSubprocessLaunch:
    def test_successful_launch(self, tmp_path):
        from llm.server_manager import start_local_server
        config = _make_config(tmp_path)

        with patch("llm.server_manager.is_available", side_effect=[False, True]), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            MockPopen.return_value = mock_proc
            start_local_server(config)

    def test_server_exits_early(self, tmp_path):
        from llm.server_manager import start_local_server
        config = _make_config(tmp_path)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"), \
             patch("pathlib.Path.read_text", return_value="Error: VRAM allocation failed\nLine 2"):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = 1
            mock_proc.returncode = 1
            MockPopen.return_value = mock_proc
            start_local_server(config)

    def test_server_exits_early_no_vram_hint(self, tmp_path):
        from llm.server_manager import start_local_server
        config = _make_config(tmp_path)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"), \
             patch("pathlib.Path.read_text", return_value="Normal exit, no GPU error"):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = 1
            mock_proc.returncode = 0
            MockPopen.return_value = mock_proc
            start_local_server(config)

    def test_timeout_no_response(self, tmp_path):
        from llm.server_manager import start_local_server
        config = _make_config(tmp_path)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            MockPopen.return_value = mock_proc
            start_local_server(config)

    def test_launch_exception(self, tmp_path):
        from llm.server_manager import start_local_server
        config = _make_config(tmp_path)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen", side_effect=OSError("Cannot start")), \
             patch("time.sleep"):
            start_local_server(config)

    def test_custom_env(self, tmp_path):
        from llm.server_manager import start_local_server
        config = _make_config(tmp_path, {"local_server_env": {"HSA_OVERRIDE_GFX_VERSION": "10.3.0"}})

        with patch("llm.server_manager.is_available", side_effect=[False, True]), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            MockPopen.return_value = mock_proc
            start_local_server(config)


# ─── Model mismatch with exception (lines 47-48) ────────────────────────────
class TestModelMismatchException:
    def test_httpx_exception_in_model_check(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
            "local_server_enabled": True,
            "llamacpp_host": "http://localhost:8080",
            "local_server_model": "E:\\models\\qwen.gguf",
        }.get(k, d)

        # First call: is_available returns True (server running)
        # Then httpx call for model info raises exception
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection reset")
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("llm.server_manager.is_available", return_value=True), \
             patch("httpx.Client") as MockClient:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_ctx
            start_local_server(mock_config)


# ─── Linux paths (lines 63, 197, 296-297) ───────────────────────────────────
class TestLinuxPaths:
    def test_mismatch_linux_kill(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
            "local_server_enabled": True,
            "llamacpp_host": "http://localhost:8080",
            "local_server_model": "E:\\models\\qwen.gguf",
        }.get(k, d)

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "E:/models/old.gguf"}]}
        mock_client.get.return_value = mock_resp

        with patch("llm.server_manager.is_available", side_effect=[True, False, True]), \
             patch("httpx.Client") as MockClient, \
             patch("sys.platform", "linux"), \
             patch("os.system"), \
             patch("time.sleep"):
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_ctx
            start_local_server(mock_config)

    def test_stop_linux_orphan(self):
        import llm.server_manager as sm
        from llm.server_manager import stop_local_server
        sm._process = None

        with patch("sys.platform", "linux"), \
             patch("os.system") as mock_sys:
            stop_local_server()
            mock_sys.assert_called_once()

    def test_telemetry_linux(self):
        import llm.server_manager as sm
        from llm.server_manager import get_system_telemetry
        sm._process = None

        meminfo = "MemTotal:       16384000 kB\nMemAvailable:   10000000 kB\n"

        with patch("sys.platform", "linux"), \
             patch("builtins.open", mock_open(read_data=meminfo)):
            result = get_system_telemetry()
            assert result["ram_total"] > 0

    def test_telemetry_linux_with_pid(self):
        import llm.server_manager as sm
        from llm.server_manager import get_system_telemetry
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 12345
        sm._process = mock_proc

        meminfo = "MemTotal:       16384000 kB\nMemAvailable:   10000000 kB\n"
        status = "VmRSS:         1048576 kB\n"

        def open_side_effect(path, *args, **kwargs):
            p = str(path)
            if "meminfo" in p:
                return mock_open(read_data=meminfo)()
            elif "status" in p:
                return mock_open(read_data=status)()
            return mock_open()()

        with patch("sys.platform", "linux"), \
             patch("builtins.open", side_effect=open_side_effect):
            result = get_system_telemetry()
            assert result["server_pid"] == 12345
            assert result["server_memory_mb"] > 0

    def test_telemetry_linux_no_memtotal(self):
        import llm.server_manager as sm
        from llm.server_manager import get_system_telemetry
        sm._process = None

        with patch("sys.platform", "linux"), \
             patch("builtins.open", mock_open(read_data="Bogus: data\n")):
            result = get_system_telemetry()
            assert result["ram_total"] == 0
