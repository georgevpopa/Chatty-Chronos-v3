import os
import platform
import pytest
from tools.shell import ExecuteCommand

def test_execute_command_success():
    cmd = ExecuteCommand()
    if platform.system() == "Windows":
        result = cmd.execute("echo test_hello")
        assert "test_hello" in result
    else:
        result = cmd.execute("echo test_hello")
        assert "test_hello" in result

def test_execute_command_failure():
    cmd = ExecuteCommand()
    result = cmd.execute("non_existent_command_xyz123")
    assert "✗" in result

def test_execute_command_with_cwd(tmp_path):
    cmd = ExecuteCommand()
    if platform.system() == "Windows":
        # cmd on windows uses cd to change directory, but we can test via dir
        result = cmd.execute("cd", cwd=str(tmp_path))
        # The result of `cd` without args in Windows cmd is the current directory
        assert str(tmp_path).replace("\\", "\\\\") in repr(result) or str(tmp_path) in result
    else:
        result = cmd.execute("pwd", cwd=str(tmp_path))
        assert str(tmp_path) in result
