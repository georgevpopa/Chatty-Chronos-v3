"""Tests for llm/server_manager.py — llama-server process lifecycle."""
import subprocess
import sys
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open, PropertyMock
from pathlib import Path


# ─── is_available ─────────────────────────────────────────────────────────────
class TestIsAvailable:
    def test_server_responds_200(self):
        from llm.server_manager import is_available
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            assert is_available("http://localhost:8080") is True

    def test_server_responds_non_200(self):
        from llm.server_manager import is_available
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            assert is_available("http://localhost:8080") is False

    def test_server_unreachable(self):
        from llm.server_manager import is_available
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.side_effect = Exception("Connection refused")
            assert is_available("http://localhost:8080") is False

    def test_server_timeout(self):
        from llm.server_manager import is_available
        import httpx
        with patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.side_effect = httpx.TimeoutException("timeout")
            assert is_available("http://localhost:8080") is False


# ─── start_local_server — disabled ────────────────────────────────────────────
class TestStartServerDisabled:
    def test_disabled_does_nothing(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.return_value = False
        start_local_server(mock_config)
        # No crash = success


# ─── start_local_server — already running ─────────────────────────────────────
class TestStartServerAlreadyRunning:
    def test_matching_model_returns_early(self):
        from llm.server_manager import start_local_server, is_available
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
            "local_server_enabled": True,
            "llamacpp_host": "http://localhost:8080",
            "local_server_model": "E:\\models\\qwen.gguf",
        }.get(k, d)

        mock_resp_health = MagicMock()
        mock_resp_health.status_code = 200

        mock_resp_models = MagicMock()
        mock_resp_models.status_code = 200
        mock_resp_models.json.return_value = {"data": [{"id": "E:/models/qwen.gguf"}]}

        mock_client = MagicMock()
        mock_client.get.side_effect = lambda url: mock_resp_models if "models" in url else mock_resp_health

        with patch("llm.server_manager.is_available", return_value=True), \
             patch("httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value = mock_client
            start_local_server(mock_config)

    def test_mismatched_model_kills_and_restarts(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
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
        }.get(k, d)

        mock_resp_health = MagicMock()
        mock_resp_health.status_code = 200

        mock_resp_models = MagicMock()
        mock_resp_models.status_code = 200
        mock_resp_models.json.return_value = {"data": [{"id": "E:/models/old.gguf"}]}

        mock_client = MagicMock()
        mock_client.get.side_effect = lambda url: mock_resp_models if "models" in url else mock_resp_health

        with patch("llm.server_manager.is_available", side_effect=[True, False, True]), \
             patch("httpx.Client") as MockClient, \
             patch("os.system"), \
             patch("time.sleep"), \
             patch("os.path.exists", return_value=True), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("subprocess.Popen") as MockPopen, \
             patch("builtins.open", mock_open()):
            MockClient.return_value.__enter__.return_value = mock_client
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            MockPopen.return_value = mock_proc
            mock_config.dir = Path("E:/tmp")
            start_local_server(mock_config)


# ─── start_local_server — missing config ──────────────────────────────────────
class TestStartServerMissingConfig:
    def test_no_bin_path(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
            "local_server_enabled": True,
            "llamacpp_host": "http://localhost:8080",
            "local_server_model": "E:\\models\\qwen.gguf",
            "local_server_bin": "",
        }.get(k, d)

        with patch("llm.server_manager.is_available", return_value=False):
            start_local_server(mock_config)

    def test_bin_not_found(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
            "local_server_enabled": True,
            "llamacpp_host": "http://localhost:8080",
            "local_server_model": "E:\\models\\qwen.gguf",
            "local_server_bin": "E:\\llama\\server.exe",
        }.get(k, d)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=False):
            start_local_server(mock_config)

    def test_no_model_path(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
            "local_server_enabled": True,
            "llamacpp_host": "http://localhost:8080",
            "local_server_model": "",
            "local_server_bin": "E:\\llama\\server.exe",
        }.get(k, d)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True):
            start_local_server(mock_config)

    def test_model_not_found(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
            "local_server_enabled": True,
            "llamacpp_host": "http://localhost:8080",
            "local_server_model": "E:\\models\\qwen.gguf",
            "local_server_bin": "E:\\llama\\server.exe",
        }.get(k, d)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", side_effect=lambda p: "server" in p):
            start_local_server(mock_config)


# ─── start_local_server — successful launch ──────────────────────────────────
class TestStartServerSuccess:
    def test_successful_launch(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
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
        }.get(k, d)

        with patch("llm.server_manager.is_available", side_effect=[False, True]), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"), \
             patch("builtins.open", mock_open()):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            MockPopen.return_value = mock_proc

            mock_config.dir = Path("E:/tmp")
            start_local_server(mock_config)

    def test_server_exits_early(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
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
        }.get(k, d)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"), \
             patch("builtins.open", mock_open()) as mock_fo:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = 1  # Process exited
            mock_proc.returncode = 1
            MockPopen.return_value = mock_proc

            mock_log_file = MagicMock()
            mock_log_file.read_text.return_value = "Error: VRAM allocation failed\nLine 2\nLine 3"
            with patch("pathlib.Path.read_text", return_value="Error: VRAM allocation failed\nLine 2\nLine 3"):
                mock_config.dir = Path("E:/tmp")
                start_local_server(mock_config)

    def test_timeout_no_response(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
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
        }.get(k, d)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"), \
             patch("builtins.open", mock_open()):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None  # Process alive but never ready
            MockPopen.return_value = mock_proc
            mock_config.dir = Path("E:/tmp")
            start_local_server(mock_config)

    def test_launch_exception(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
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
        }.get(k, d)

        with patch("llm.server_manager.is_available", return_value=False), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen", side_effect=OSError("Cannot start")), \
             patch("time.sleep"), \
             patch("builtins.open", mock_open()):
            mock_config.dir = Path("E:/tmp")
            start_local_server(mock_config)

    def test_custom_env_variables(self):
        from llm.server_manager import start_local_server
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda k, d=None: {
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
            "local_server_env": {"HSA_OVERRIDE_GFX_VERSION": "10.3.0"},
        }.get(k, d)

        with patch("llm.server_manager.is_available", side_effect=[False, True]), \
             patch("os.path.expandvars", side_effect=lambda x: x), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen") as MockPopen, \
             patch("time.sleep"), \
             patch("builtins.open", mock_open()):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            MockPopen.return_value = mock_proc
            mock_config.dir = Path("E:/tmp")
            start_local_server(mock_config)


# ─── stop_local_server ────────────────────────────────────────────────────────
class TestStopLocalServer:
    def test_stop_active_process(self):
        import llm.server_manager as sm
        from llm.server_manager import stop_local_server
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        sm._process = mock_proc

        with patch("os.system"), patch("time.sleep"):
            stop_local_server()
            mock_proc.terminate.assert_called_once()
            assert sm._process is None

    def test_stop_timeout_kills(self):
        import llm.server_manager as sm
        from llm.server_manager import stop_local_server
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)
        sm._process = mock_proc

        with patch("os.system"), patch("time.sleep"):
            stop_local_server()
            mock_proc.kill.assert_called_once()
            assert sm._process is None

    def test_stop_already_dead(self):
        import llm.server_manager as sm
        from llm.server_manager import stop_local_server
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # Already dead
        sm._process = mock_proc

        with patch("os.system"), patch("time.sleep"):
            stop_local_server()

    def test_stop_no_process(self):
        import llm.server_manager as sm
        from llm.server_manager import stop_local_server
        sm._process = None

        with patch("os.system"), patch("time.sleep"):
            stop_local_server()

    def test_stop_orphan_kills(self):
        import llm.server_manager as sm
        from llm.server_manager import stop_local_server
        sm._process = None

        with patch("os.system") as mock_sys:
            stop_local_server()
            mock_sys.assert_called_once()


# ─── restart_with_model ──────────────────────────────────────────────────────
class TestRestartWithModel:
    def test_restart_success(self):
        from llm.server_manager import restart_with_model
        mock_config = MagicMock()
        mock_config.get.return_value = "E:\\models\\old.gguf"

        with patch("llm.server_manager.stop_local_server"), \
             patch("time.sleep"), \
             patch("os.path.dirname", return_value="E:\\models"), \
             patch("os.path.exists", return_value=True), \
             patch("llm.server_manager.start_local_server"):
            result = restart_with_model(mock_config, "qwen.gguf")
            assert result is True

    def test_restart_model_not_found(self):
        from llm.server_manager import restart_with_model
        mock_config = MagicMock()
        mock_config.get.return_value = "E:\\models\\old.gguf"

        with patch("llm.server_manager.stop_local_server"), \
             patch("time.sleep"), \
             patch("os.path.dirname", return_value="E:\\models"), \
             patch("os.path.exists", return_value=False):
            result = restart_with_model(mock_config, "missing.gguf")
            assert result is False

    def test_restart_no_models_dir(self):
        from llm.server_manager import restart_with_model
        mock_config = MagicMock()
        mock_config.get.return_value = ""

        with patch("llm.server_manager.stop_local_server"), \
             patch("time.sleep"), \
             patch("os.path.exists", return_value=False):
            result = restart_with_model(mock_config, "qwen.gguf")
            assert result is False


# ─── get_system_telemetry ─────────────────────────────────────────────────────
class TestGetSystemTelemetry:
    def _make_win32_telemetry_test(self, with_pid=False):
        """Helper — runs get_system_telemetry with a win32 ctypes mock."""
        import llm.server_manager as sm
        import ctypes
        from llm.server_manager import get_system_telemetry

        if with_pid:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_proc.pid = 12345
            sm._process = mock_proc
        else:
            sm._process = None

        # Capture the MEMORYSTATUSEX instance so we can set its fields
        captured_stat = [None]

        class FakeStructure:
            def __init__(self):
                self.dwLength = 0
                self.ullTotalPhys = 0
                self.ullAvailPhys = 0
                self.dwMemoryLoad = 0

        def fake_sizeof(obj):
            return 72  # sizeof(MEMORYSTATUSEX) on 64-bit

        def fake_GlobalMemoryStatusEx(stat):
            # Simulate the OS filling in the struct
            stat.ullTotalPhys = 16 * 1024 ** 3  # 16 GB
            stat.ullAvailPhys = 8 * 1024 ** 3   # 8 GB free
            stat.dwMemoryLoad = 50

        with patch("sys.platform", "win32"), \
             patch.object(ctypes, "Structure", FakeStructure), \
             patch.object(ctypes, "sizeof", side_effect=fake_sizeof), \
             patch.object(ctypes, "byref", lambda x: x), \
             patch("ctypes.windll.kernel32.GlobalMemoryStatusEx", side_effect=fake_GlobalMemoryStatusEx), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "WorkingSetSize=2147483648\n"
            result = get_system_telemetry()
            return result

    def test_telemetry_with_server_pid(self):
        result = self._make_win32_telemetry_test(with_pid=True)
        assert "ram_total" in result
        assert result["server_pid"] == 12345
        assert result["ram_total"] == 16.0
        assert result["server_memory_mb"] == 2048.0

    def test_telemetry_no_server(self):
        result = self._make_win32_telemetry_test(with_pid=False)
        assert result["server_pid"] is None
        assert result["ram_total"] == 16.0

    def test_telemetry_linux(self):
        import llm.server_manager as sm
        from llm.server_manager import get_system_telemetry
        sm._process = None

        meminfo = "MemTotal:       16384000 kB\nMemFree:         8192000 kB\nMemAvailable:   10000000 kB\n"

        with patch("sys.platform", "linux"), \
             patch("builtins.open", mock_open(read_data=meminfo)):
            result = get_system_telemetry()
            assert result["platform"] == "linux"
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

        with patch("sys.platform", "linux"), \
             patch("builtins.open", mock_open(read_data=meminfo)):
            # Need to handle two different file reads
            def open_side_effect(path, *args, **kwargs):
                if "meminfo" in str(path):
                    return mock_open(read_data=meminfo)()
                elif "status" in str(path):
                    return mock_open(read_data=status)()
                return mock_open()()
            with patch("builtins.open", side_effect=open_side_effect):
                result = get_system_telemetry()
                assert result["server_pid"] == 12345
                assert result["server_memory_mb"] > 0

    def test_telemetry_exception_handled(self):
        import llm.server_manager as sm
        from llm.server_manager import get_system_telemetry
        import ctypes

        sm._process = None

        class FakeStructure:
            pass

        def fake_sizeof(obj):
            raise Exception("ctypes error")

        with patch("sys.platform", "win32"), \
             patch.object(ctypes, "Structure", FakeStructure), \
             patch.object(ctypes, "sizeof", side_effect=fake_sizeof):
            result = get_system_telemetry()
            assert result["ram_total"] == 0
