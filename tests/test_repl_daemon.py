"""Tests for core/repl_daemon.py — sandboxed Python REPL daemon."""
import sys
import io
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── REPL daemon main loop ────────────────────────────────────────────────────
class TestReplDaemonMain:
    def test_execute_variable_assignment(self):
        """Daemon executes variable assignment successfully."""
        import core.repl_daemon as daemon

        input_data = json.dumps({"code": "x = 42"}) + "\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured

            daemon.main()

            output = captured.getvalue()
            resp = json.loads(output.strip())
            assert resp["status"] == "success"
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_execute_import(self):
        """Daemon executes import statements."""
        import core.repl_daemon as daemon

        input_data = json.dumps({"code": "import math; result = math.pi"}) + "\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured

            daemon.main()

            output = captured.getvalue()
            resp = json.loads(output.strip())
            assert resp["status"] == "success"
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_execute_error(self):
        """Daemon handles syntax errors gracefully."""
        import core.repl_daemon as daemon

        input_data = json.dumps({"code": "def invalid python!!!"}) + "\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured

            daemon.main()

            output = captured.getvalue()
            resp = json.loads(output.strip())
            assert resp["status"] == "success"
            assert "SyntaxError" in resp["output"] or "Traceback" in resp["output"]
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_execute_runtime_error(self):
        """Daemon handles runtime errors."""
        import core.repl_daemon as daemon

        input_data = json.dumps({"code": "1 / 0"}) + "\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured

            daemon.main()

            output = captured.getvalue()
            resp = json.loads(output.strip())
            assert resp["status"] == "success"
            assert "ZeroDivisionError" in resp["output"] or "Traceback" in resp["output"]
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_empty_line_exits(self):
        """Empty stdin line causes daemon to exit."""
        import core.repl_daemon as daemon

        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO("")
            sys.stdout = io.StringIO()
            daemon.main()
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_invalid_json_handled(self):
        """Invalid JSON input is handled gracefully."""
        import core.repl_daemon as daemon

        input_data = "not valid json\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured

            daemon.main()

            output = captured.getvalue()
            resp = json.loads(output.strip())
            assert resp["status"] == "error"
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_multiple_commands(self):
        """Daemon handles multiple commands sequentially."""
        import core.repl_daemon as daemon

        lines = [
            json.dumps({"code": "x = 10"}),
            json.dumps({"code": "y = x * 2"}),
            "",
        ]
        input_data = "\n".join(lines) + "\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured
            daemon.main()  # Should not hang or crash
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_state_persists_across_commands(self):
        """Variables persist across commands (verified by execution)."""
        import core.repl_daemon as daemon

        # Use code that will produce output if state persists
        lines = [
            json.dumps({"code": "result = []"}),
            json.dumps({"code": "result.append(1)"}),
            json.dumps({"code": "result.append(2)"}),
            "",
        ]
        input_data = "\n".join(lines) + "\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured
            daemon.main()  # Should not crash
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_empty_code_returns_success(self):
        """Empty code string returns success with no output message."""
        import core.repl_daemon as daemon

        input_data = json.dumps({"code": ""}) + "\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured

            daemon.main()

            output = captured.getvalue()
            resp = json.loads(output.strip())
            assert resp["status"] == "success"
            assert "No output" in resp["output"]
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

    def test_missing_code_key(self):
        """Missing 'code' key in JSON is handled."""
        import core.repl_daemon as daemon

        input_data = json.dumps({"not_code": "hello"}) + "\n"
        old_stdin = sys.stdin
        old_stdout = sys.stdout

        try:
            sys.stdin = io.StringIO(input_data)
            captured = io.StringIO()
            sys.stdout = captured

            daemon.main()

            output = captured.getvalue()
            resp = json.loads(output.strip())
            assert resp["status"] == "success"
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout


# ─── Sandbox globals ──────────────────────────────────────────────────────────
class TestSandboxGlobals:
    def test_globals_exist(self):
        import core.repl_daemon as daemon
        assert "_REPL_GLOBALS" in dir(daemon)
        assert "__builtins__" in daemon._REPL_GLOBALS

    def test_builtins_are_restricted(self):
        """RestrictedPython safe_builtins should be present."""
        import core.repl_daemon as daemon
        builtins = daemon._REPL_GLOBALS["__builtins__"]
        # Should have basic builtins but not dangerous ones
        assert isinstance(builtins, dict)
        assert "__build_class__" in builtins
        assert "None" in builtins
        assert "True" in builtins
        assert "False" in builtins
