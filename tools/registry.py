"""Tool registry — discovers and provides all available tools.

Built-in tools are always registered. Additionally, any loaded Plugin that
exposes a `tools` list will have its tools merged in automatically, allowing
external plugins to extend the agent's capabilities without modifying this file.
"""
from tools.filesystem import ReadFile, WriteFile, SearchReplace, ListDirectory, GlobSearch, Grep, MoveFile
from tools.shell import ExecuteCommand
from tools.agent_delegator import DelegateSubtask
from tools.human import AskUser
from tools.web import FetchWebpage
from tools.python_repl import RunPython
from tools.memory_tools import StoreMemory, SearchMemory

# ─── Built-in tool set (always available) ───────────────────────────────────
_BUILTIN_TOOLS = [
    ReadFile(),
    WriteFile(),
    SearchReplace(),
    ListDirectory(),
    GlobSearch(),
    Grep(),
    MoveFile(),
    ExecuteCommand(),
    DelegateSubtask(),
    AskUser(),
    FetchWebpage(),
    RunPython(),
    StoreMemory(),
    SearchMemory(),
]


def get_all_tools():
    """Return all available tool instances (built-in + plugin-contributed)."""
    tools = list(_BUILTIN_TOOLS)

    # Merge in tools contributed by loaded plugins
    try:
        from plugins.loader import get_loaded_plugins
        for plugin in get_loaded_plugins():
            plugin_tools = plugin.get_tools()
            if plugin_tools:
                existing_names = {t.name for t in tools}
                for pt in plugin_tools:
                    if pt.name not in existing_names:
                        tools.append(pt)
                        existing_names.add(pt.name)
    except Exception:
        pass  # Plugins are optional — never break the agent

    return tools


def get_tool_by_name(name: str):
    """Find a tool by its name."""
    for tool in get_all_tools():
        if tool.name == name:
            return tool
    return None


def get_ollama_tools_schema():
    """Get all tools in Ollama-compatible format."""
    return [t.to_ollama_schema() for t in get_all_tools()]


def register_tool(tool):
    """Dynamically register a tool at runtime (used by agents and tests).

    The tool will appear in get_all_tools() for the duration of the process.
    Note: built-in tools registered via _BUILTIN_TOOLS always take precedence
    (name collision is silently ignored).
    """
    existing_names = {t.name for t in _BUILTIN_TOOLS}
    if tool.name not in existing_names:
        _BUILTIN_TOOLS.append(tool)