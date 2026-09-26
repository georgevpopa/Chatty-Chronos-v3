"""Tests for tools/registry.py — tool discovery and registration."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── get_all_tools ────────────────────────────────────────────────────────────
class TestGetAllTools:
    def test_returns_builtin_tools(self):
        """get_all_tools returns all built-in tools."""
        from tools.registry import get_all_tools
        tools = get_all_tools()
        assert len(tools) >= 14
        names = [t.name for t in tools]
        assert "read_file" in names
        assert "write_file" in names
        assert "execute_command" in names
        assert "grep" in names
        assert "run_python" in names
        assert "store_memory" in names
        assert "search_memory" in names

    def test_includes_all_builtin_names(self):
        """All expected built-in tool names are present."""
        from tools.registry import get_all_tools
        tools = get_all_tools()
        names = {t.name for t in tools}
        expected = {
            "read_file", "write_file", "search_replace", "list_directory",
            "glob_search", "grep", "move_file", "execute_command",
            "delegate_subtask", "ask_user", "fetch_webpage", "run_python",
            "store_memory", "search_memory"
        }
        assert expected.issubset(names)

    def test_plugin_tools_merged(self):
        """Plugin-contributed tools are merged into the list."""
        from tools.registry import get_all_tools

        mock_tool = MagicMock()
        mock_tool.name = "custom_plugin_tool"

        mock_plugin = MagicMock()
        mock_plugin.get_tools.return_value = [mock_tool]

        with patch("plugins.loader.get_loaded_plugins", return_value=[mock_plugin]):
            tools = get_all_tools()
            names = [t.name for t in tools]
            assert "custom_plugin_tool" in names

    def test_plugin_tool_no_duplicate(self):
        """Plugin tool with same name as built-in is not added."""
        from tools.registry import get_all_tools

        mock_tool = MagicMock()
        mock_tool.name = "read_file"  # Same as built-in

        mock_plugin = MagicMock()
        mock_plugin.get_tools.return_value = [mock_tool]

        with patch("plugins.loader.get_loaded_plugins", return_value=[mock_plugin]):
            tools = get_all_tools()
            read_file_count = sum(1 for t in tools if t.name == "read_file")
            assert read_file_count == 1

    def test_no_plugins_still_works(self):
        """Works when no plugins are loaded."""
        from tools.registry import get_all_tools

        with patch("plugins.loader.get_loaded_plugins", return_value=[]):
            tools = get_all_tools()
            assert len(tools) >= 14

    def test_plugin_exception_handled(self):
        """Plugin exception doesn't break tool loading."""
        from tools.registry import get_all_tools

        with patch("plugins.loader.get_loaded_plugins", side_effect=Exception("Plugin error")):
            tools = get_all_tools()
            assert len(tools) >= 14


# ─── get_tool_by_name ────────────────────────────────────────────────────────
class TestGetToolByName:
    def test_finds_existing_tool(self):
        from tools.registry import get_tool_by_name
        tool = get_tool_by_name("read_file")
        assert tool is not None
        assert tool.name == "read_file"

    def test_returns_none_for_unknown(self):
        from tools.registry import get_tool_by_name
        tool = get_tool_by_name("nonexistent_tool")
        assert tool is None

    def test_finds_all_builtin_tools(self):
        from tools.registry import get_tool_by_name
        for name in ["read_file", "write_file", "grep", "execute_command", "run_python"]:
            tool = get_tool_by_name(name)
            assert tool is not None, f"Tool '{name}' not found"


# ─── get_ollama_tools_schema ─────────────────────────────────────────────────
class TestGetOllamaToolsSchema:
    def test_returns_list_of_dicts(self):
        from tools.registry import get_ollama_tools_schema
        schema = get_ollama_tools_schema()
        assert isinstance(schema, list)
        assert len(schema) >= 14

    def test_each_entry_has_function(self):
        from tools.registry import get_ollama_tools_schema
        schema = get_ollama_tools_schema()
        for entry in schema:
            assert "function" in entry
            assert "name" in entry["function"]
            assert "parameters" in entry["function"]

    def test_schema_includes_read_file(self):
        from tools.registry import get_ollama_tools_schema
        schema = get_ollama_tools_schema()
        names = [e["function"]["name"] for e in schema]
        assert "read_file" in names


# ─── register_tool ────────────────────────────────────────────────────────────
class TestRegisterTool:
    def test_register_new_tool(self):
        from tools.registry import register_tool, get_all_tools, _BUILTIN_TOOLS

        mock_tool = MagicMock()
        mock_tool.name = "dynamic_test_tool"

        initial_count = len(_BUILTIN_TOOLS)
        register_tool(mock_tool)

        tools = get_all_tools()
        names = [t.name for t in tools]
        assert "dynamic_test_tool" in names

        # Cleanup
        _BUILTIN_TOOLS[:] = [t for t in _BUILTIN_TOOLS if t.name != "dynamic_test_tool"]

    def test_register_existing_tool_ignored(self):
        """Registering a tool with same name as built-in is silently ignored."""
        from tools.registry import register_tool, get_all_tools, _BUILTIN_TOOLS

        mock_tool = MagicMock()
        mock_tool.name = "read_file"  # Already exists

        initial_count = len(_BUILTIN_TOOLS)
        register_tool(mock_tool)

        # Should not add duplicate
        assert len(_BUILTIN_TOOLS) == initial_count

    def test_multiple_registrations(self):
        """Multiple different tools can be registered."""
        from tools.registry import register_tool, get_all_tools, _BUILTIN_TOOLS

        tools_to_add = []
        for i in range(3):
            t = MagicMock()
            t.name = f"dynamic_tool_{i}"
            tools_to_add.append(t)
            register_tool(t)

        all_tools = get_all_tools()
        names = [t.name for t in all_tools]
        for t in tools_to_add:
            assert t.name in names

        # Cleanup
        _BUILTIN_TOOLS[:] = [t for t in _BUILTIN_TOOLS if not t.name.startswith("dynamic_tool_")]
