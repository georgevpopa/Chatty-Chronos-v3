"""Shell tool — execute system commands with safety checks."""
import subprocess
import platform
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
from tools.base import Tool

MAX_OUTPUT = 4000
TIMEOUT = 120

class ExecuteCommandSchema(BaseModel):
    command: str = Field(..., description="The shell command to execute")
    cwd: Optional[str] = Field(default=None, description="Working directory (optional)")
    timeout: Optional[int] = Field(default=None, description="Command timeout in seconds (default: 120)")

class ExecuteCommand(Tool):
    def __init__(self):
        super().__init__(
            name="execute_command",
            description="Run a shell command and return its output. Use for builds, tests, git, etc.",
            input_schema=ExecuteCommandSchema,
            requires_permission=True,
        )

    def execute(self, command: str, cwd: str = None, timeout: int = None, **kwargs) -> str:
        work_dir = Path(cwd).expanduser().resolve() if cwd else None
        exec_timeout = timeout if timeout is not None else TIMEOUT

        if platform.system() == "Windows":
            shell_cmd = ["cmd", "/c", command]
        else:
            shell_cmd = ["bash", "-c", command]

        try:
            result = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                cwd=work_dir,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += ("\n" if output else "") + result.stderr

            if not output.strip():
                output = "(no output)"

            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + f"\n\n[Truncated — {len(output)} chars total]"

            status = "✓" if result.returncode == 0 else f"✗ (exit code {result.returncode})"
            return f"[{status}]\n{output}"

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {exec_timeout}s"
        except Exception as e:
            return f"Error executing command: {e}"
