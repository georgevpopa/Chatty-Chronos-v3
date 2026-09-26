"""Tests for tools/python_repl.py and core/repl_daemon.py — sandboxed Python execution."""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path
import subprocess
import threading


# ─── RunPython tool ───────────────────────────────────────────────────────────
class TestRunPython:
    def test_tool_creation(self):
        from tools.python_repl import RunPython
        tool = RunPython()
        assert tool.name == "run_python"
        assert tool.requires_permission is True

    def test_tool_schema(self):
        from tools.python_repl import RunPython
        tool = RunPython()
        schema = tool.to_ollama_schema()
        assert schema["function"]["name"] == "run_python"
        assert "code" in schema["function"]["parameters"]["properties"]

    @patch("tools.python_repl.get_daemon")
    def test_execute_success(self, mock_get_daemon):
        """Execute code returns output from daemon."""
        mock_daemon = MagicMock()
        mock_daemon.poll.return_value = None  # Process is alive
        mock_daemon.stdout.readline.return_value = json.dumps({
            "status": "success",
            "output": "42"
        })
        mock_get_daemon.return_value = mock_daemon

        from tools.python_repl import RunPython
        tool = RunPython()
        result = tool.execute(code="print(42)")

        assert "42" in result

    @patch("tools.python_repl.get_daemon")
    def test_execute_no_output(self, mock_get_daemon):
        """Execute code with no output returns success message."""
        mock_daemon = MagicMock()
        mock_daemon.poll.return_value = None
        mock_daemon.stdout.readline.return_value = json.dumps({
            "status": "success",
            "output": "(Code executed successfully. No output generated.)"
        })
        mock_get_daemon.return_value = mock_daemon

        from tools.python_repl import RunPython
        tool = RunPython()
        result = tool.execute(code="x = 1")

        assert "No output" in result or "executed" in result.lower()

    @patch("tools.python_repl.get_daemon")
    def test_execute_daemon_error(self, mock_get_daemon):
        """Daemon error response is returned."""
        mock_daemon = MagicMock()
        mock_daemon.poll.return_value = None
        mock_daemon.stdout.readline.return_value = json.dumps({
            "status": "error",
            "output": "NameError: name 'xyz' is not defined"
        })
        mock_get_daemon.return_value = mock_daemon

        from tools.python_repl import RunPython
        tool = RunPython()
        result = tool.execute(code="print(xyz)")

        assert "NameError" in result

    @patch("tools.python_repl.get_daemon")
    def test_execute_timeout(self, mock_get_daemon):
        """Timeout kills daemon and returns error."""
        mock_daemon = MagicMock()
        mock_daemon.poll.return_value = None

        # Simulate a thread that never finishes
        def slow_readline():
            import time
            time.sleep(10)
            return ""

        mock_daemon.stdout.readline = slow_readline
        mock_get_daemon.return_value = mock_daemon

        from tools.python_repl import RunPython, _daemon_process, _daemon_lock
        import tools.python_repl as repl
        repl._daemon_process = mock_daemon

        tool = RunPython()
        result = tool.execute(code="import time; time.sleep(100)")

        assert "timed out" in result.lower() or "killed" in result.lower()
        # Daemon should be reset
        assert repl._daemon_process is None

    @patch("tools.python_repl.get_daemon")
    def test_execute_daemon_died(self, mock_get_daemon):
        """Dead daemon returns error."""
        mock_daemon = MagicMock()
        mock_daemon.poll.return_value = None
        mock_daemon.stdout.readline.return_value = ""  # Empty response
        mock_get_daemon.return_value = mock_daemon

        from tools.python_repl import RunPython
        tool = RunPython()
        result = tool.execute(code="print(1)")

        assert "Error" in result

    @patch("tools.python_repl.get_daemon")
    def test_execute_invalid_json_response(self, mock_get_daemon):
        """Invalid JSON response returns parse error."""
        mock_daemon = MagicMock()
        mock_daemon.poll.return_value = None
        mock_daemon.stdout.readline.return_value = "not valid json {{{"
        mock_get_daemon.return_value = mock_daemon

        from tools.python_repl import RunPython
        tool = RunPython()
        result = tool.execute(code="test")

        assert "Error parsing" in result


# ─── get_daemon ───────────────────────────────────────────────────────────────
class TestGetDaemon:
    def test_creates_new_daemon(self):
        """get_daemon creates a new subprocess when none exists."""
        import tools.python_repl as repl
        repl._daemon_process = None

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        with patch("tools.python_repl.subprocess.Popen", return_value=mock_proc):
            result = repl.get_daemon()

        assert result is mock_proc
        repl._daemon_process = None

    def test_reuses_existing_daemon(self):
        """get_daemon reuses existing live daemon."""
        import tools.python_repl as repl
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        repl._daemon_process = mock_proc

        result = repl.get_daemon()
        assert result is mock_proc
        repl._daemon_process = None

    def test_restarts_dead_daemon(self):
        """get_daemon restarts when daemon has exited."""
        import tools.python_repl as repl
        old_proc = MagicMock()
        old_proc.poll.return_value = 1  # Exited
        repl._daemon_process = old_proc

        new_proc = MagicMock()
        new_proc.poll.return_value = None

        with patch("tools.python_repl.subprocess.Popen", return_value=new_proc):
            result = repl.get_daemon()

        assert result is new_proc
        repl._daemon_process = None


# ─── repl_daemon ──────────────────────────────────────────────────────────────
class TestReplDaemon:
    def test_daemon_imports(self):
        """repl_daemon module can be imported."""
        from core import repl_daemon
        assert hasattr(repl_daemon, "main")

    def test_daemon_globals_exist(self):
        """repl_daemon has the required sandbox globals."""
        from core import repl_daemon
        assert "_REPL_GLOBALS" in dir(repl_daemon)
        assert "__builtins__" in repl_daemon._REPL_GLOBALS
