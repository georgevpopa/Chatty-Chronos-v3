"""Stateful Python execution tool (Sandboxed via subprocess)."""
import json
import subprocess
import os
import threading
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from tools.base import Tool

_daemon_process = None
_daemon_lock = threading.Lock()

def get_daemon():
    global _daemon_process
    with _daemon_lock:
        if _daemon_process is None or _daemon_process.poll() is not None:
            daemon_path = Path(os.getcwd()) / "core" / "repl_daemon.py"
            _daemon_process = subprocess.Popen(
                [sys.executable, str(daemon_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        return _daemon_process

class RunPythonSchema(BaseModel):
    code: str = Field(..., description="The Python code to execute.")

class RunPython(Tool):
    def __init__(self):
        super().__init__(
            name="run_python",
            description=(
                "Execute Python code in a sandboxed, stateful REPL (5s timeout). "
                "Variables and imports are preserved across calls. Environment is restricted for security."
            ),
            input_schema=RunPythonSchema,
            requires_permission=True,
        )

    def execute(self, code: str, **kwargs) -> str:
        daemon = get_daemon()
        req = json.dumps({"code": code})
        
        result = []
        def target():
            try:
                daemon.stdin.write(req + "\n")
                daemon.stdin.flush()
                resp_line = daemon.stdout.readline()
                result.append(resp_line)
            except Exception as e:
                result.append(json.dumps({"status": "error", "output": str(e)}))

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=5.0)
        
        if thread.is_alive():
            daemon.kill()
            with _daemon_lock:
                global _daemon_process
                _daemon_process = None
            return "Error: Execution timed out after 5 seconds. Process was killed."
            
        if not result or not result[0]:
            return "Error: REPL daemon died unexpectedly."
            
        try:
            resp = json.loads(result[0])
            return resp.get("output", "")
        except json.JSONDecodeError:
            return f"Error parsing daemon response: {result[0]}"
