"""Tests for llm/llama_cpp_launcher.py — GPU detection and llama-server launcher."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestDetectGPU:
    def test_detect_amd(self):
        from llm.llama_cpp_launcher import detect_gpu_backend
        mock_result = MagicMock()
        mock_result.stdout = "AMD Radeon RX 580\n"
        with patch("subprocess.run", return_value=mock_result):
            assert detect_gpu_backend() == "hip"

    def test_detect_nvidia(self):
        from llm.llama_cpp_launcher import detect_gpu_backend
        mock_result = MagicMock()
        mock_result.stdout = "NVIDIA GeForce GTX 1080\n"
        with patch("subprocess.run", return_value=mock_result):
            assert detect_gpu_backend() == "vulkan"

    def test_detect_exception(self):
        from llm.llama_cpp_launcher import detect_gpu_backend
        with patch("subprocess.run", side_effect=Exception("fail")):
            assert detect_gpu_backend() == "vulkan"

    def test_detect_no_amd(self):
        from llm.llama_cpp_launcher import detect_gpu_backend
        mock_result = MagicMock()
        mock_result.stdout = "Intel UHD Graphics\n"
        with patch("subprocess.run", return_value=mock_result):
            assert detect_gpu_backend() == "vulkan"


class TestGetServerBinary:
    def test_explicit_path_exists(self):
        from llm.llama_cpp_launcher import get_server_binary
        with patch("pathlib.Path.exists", return_value=True):
            result = get_server_binary(explicit_path="/opt/llama/llama-server")
            assert result is not None
            assert str(result) == str(Path("/opt/llama/llama-server"))

    def test_env_var_used(self, monkeypatch):
        from llm.llama_cpp_launcher import get_server_binary
        monkeypatch.setenv("CHRONOS_LLAMA_SERVER", "/custom/llama-server")
        with patch("pathlib.Path.exists", return_value=True):
            result = get_server_binary()
            assert result is not None
            assert str(result) == str(Path("/custom/llama-server"))

    def test_found_on_path(self, monkeypatch):
        from llm.llama_cpp_launcher import get_server_binary
        monkeypatch.delenv("CHRONOS_LLAMA_SERVER", raising=False)
        with patch("pathlib.Path.exists", return_value=False), \
             patch("shutil.which", return_value="/usr/bin/llama-server"):
            result = get_server_binary()
            assert result is not None
            assert str(result) == str(Path("/usr/bin/llama-server"))

    def test_not_found(self, monkeypatch):
        from llm.llama_cpp_launcher import get_server_binary
        monkeypatch.delenv("CHRONOS_LLAMA_SERVER", raising=False)
        with patch("pathlib.Path.exists", return_value=False), \
             patch("shutil.which", return_value=None):
            result = get_server_binary()
            assert result is None


class TestStartServer:
    def test_success_with_explicit_binary(self):
        from llm.llama_cpp_launcher import start_server
        with patch("pathlib.Path.exists", return_value=True), \
             patch("llm.llama_cpp_launcher.detect_gpu_backend", return_value="vulkan"), \
             patch("subprocess.Popen") as mock_popen:
            result = start_server("/model.gguf", port=8080, backend="vulkan",
                                  binary_path="/opt/llama/llama-server")
            assert result is not None
            mock_popen.assert_called_once()

    def test_extra_env_applied(self):
        from llm.llama_cpp_launcher import start_server
        with patch("pathlib.Path.exists", return_value=True), \
             patch("llm.llama_cpp_launcher.detect_gpu_backend", return_value="hip"), \
             patch("subprocess.Popen") as mock_popen:
            result = start_server("/model.gguf", port=8080, backend="hip",
                                  binary_path="/opt/llama/llama-server",
                                  extra_env={"HSA_OVERRIDE_GFX_VERSION": "11.0.2"})
            assert result is not None
            call_kwargs = mock_popen.call_args
            assert call_kwargs[1]["env"]["HSA_OVERRIDE_GFX_VERSION"] == "11.0.2"

    def test_no_binary(self, monkeypatch):
        from llm.llama_cpp_launcher import start_server
        monkeypatch.delenv("CHRONOS_LLAMA_SERVER", raising=False)
        with patch("pathlib.Path.exists", return_value=False), \
             patch("shutil.which", return_value=None), \
             patch("llm.llama_cpp_launcher.detect_gpu_backend", return_value="vulkan"):
            result = start_server("/model.gguf", backend="vulkan")
            assert result is None


class TestIsServerRunning:
    def test_running(self):
        from llm.llama_cpp_launcher import is_server_running
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.get", return_value=mock_resp):
            assert is_server_running(8080) is True

    def test_not_running(self):
        from llm.llama_cpp_launcher import is_server_running
        with patch("httpx.get", side_effect=Exception("Connection refused")):
            assert is_server_running(8080) is False

    def test_non_200(self):
        from llm.llama_cpp_launcher import is_server_running
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch("httpx.get", return_value=mock_resp):
            assert is_server_running(8080) is False
