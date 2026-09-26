"""Plugin base class — all plugins inherit from this."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.base import Tool


class Plugin:
    """Base class for Chatty Chronos plugins.

    Drop a .py file in ~/.chatty-chronos/plugins/ that defines a class
    inheriting from Plugin. It will be auto-loaded on startup.

    A plugin can do two things:
    1. Register slash commands (handled by handle_command)
    2. Expose new Tool instances to the ReAct agent (via the `tools` list)

    Example — command-only plugin:

        from plugins.base import Plugin

        class GitPlugin(Plugin):
            name = "git"
            description = "Git shortcuts"
            commands = {"/git-status": "Show git status"}

            def handle_command(self, command, arg):
                if command == "/git-status":
                    import subprocess
                    return subprocess.check_output(["git", "status"]).decode()

    Example — plugin that also exposes a tool to the agent:

        from plugins.base import Plugin
        from tools.base import Tool

        class MyTool(Tool):
            def __init__(self):
                super().__init__(
                    name="my_tool",
                    description="Does something useful",
                    parameters={"input": {"type": "string", "description": "The input", "required": True}},
                    requires_permission=False,
                )
            def execute(self, input: str, **kwargs) -> str:
                return f"Result: {input}"

        class MyPlugin(Plugin):
            name = "my_plugin"
            description = "Exposes MyTool to the agent"
            tools = [MyTool()]
    """
    name: str = "unnamed"
    description: str = ""
    version: str = "0.1.0"
    commands: dict = {}       # {"/command": "description"}
    tools: list = []          # List[Tool] — exposed to the ReAct agent automatically

    def get_tools(self) -> list:
        """Return tool instances this plugin contributes to the agent."""
        return list(self.tools)

    def on_load(self):
        """Called when plugin is loaded."""
        pass

    def on_unload(self):
        """Called when plugin is unloaded."""
        pass

    def handle_command(self, command: str, arg: str) -> "str | None":
        """Handle a slash command. Return response string or None if not handled."""
        return None

    def on_message(self, role: str, content: str):
        """Called on every message (user or assistant). For hooks/logging."""
        pass
