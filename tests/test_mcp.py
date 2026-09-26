"""Tests for core/mcp_client.py and tools/mcp_tool.py — MCP client + tool wrapper."""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ─── MCPClientManager ────────────────────────────────────────────────────────
class TestMCPClientManager:
    def test_init(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()
        assert mgr.servers == {}

    def test_get_server_tools_unknown(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()
        assert mgr.get_server_tools("nonexistent") == []

    def test_get_server_tools_known(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()
        mgr.servers["myserver"] = {"tools": ["tool1", "tool2"]}
        assert mgr.get_server_tools("myserver") == ["tool1", "tool2"]

    def test_connect_already_connected(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()
        mgr.servers["myserver"] = {}
        result = asyncio.run(mgr.connect("myserver", "cmd", []))
        assert result is True

    def test_connect_success(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"

        # Build a fake async context manager that enter_async_context can consume
        class FakeAsyncCM:
            async def __aenter__(self):
                return (MagicMock(), MagicMock())
            async def __aexit__(self, *args):
                return False

        mock_transport = FakeAsyncCM()

        mock_session = MagicMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[mock_tool]))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("core.mcp_client.stdio_client", return_value=mock_transport), \
             patch("core.mcp_client.ClientSession", return_value=mock_session):
            result = asyncio.run(mgr.connect("myserver", "npx", ["-y", "server"]))
            assert result is True
            assert "myserver" in mgr.servers

    def test_connect_exception(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()

        with patch("core.mcp_client.stdio_client", side_effect=Exception("Connection failed")):
            result = asyncio.run(mgr.connect("myserver", "bad_cmd", []))
            assert result is False

    def test_call_tool_server_not_found(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()
        result = asyncio.run(mgr.call_tool("nonexistent", "tool", {}))
        assert "Error" in result

    def test_call_tool_success(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "result text"

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=MagicMock(content=[mock_block]))

        mgr.servers["myserver"] = {"session": mock_session}
        result = asyncio.run(mgr.call_tool("myserver", "test_tool", {"arg": "val"}))
        assert result == "result text"

    def test_call_tool_no_content(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=MagicMock(content=[]))

        mgr.servers["myserver"] = {"session": mock_session}
        result = asyncio.run(mgr.call_tool("myserver", "test_tool", {}))
        assert "no output" in result.lower()

    def test_call_tool_non_text_block(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()

        mock_block = MagicMock()
        mock_block.type = "image"
        mock_block.__str__ = lambda self: "image block"

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=MagicMock(content=[mock_block]))

        mgr.servers["myserver"] = {"session": mock_session}
        result = asyncio.run(mgr.call_tool("myserver", "test_tool", {}))
        assert "image block" in result

    def test_call_tool_exception(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(side_effect=Exception("Tool error"))

        mgr.servers["myserver"] = {"session": mock_session}
        result = asyncio.run(mgr.call_tool("myserver", "test_tool", {}))
        assert "Error" in result

    def test_close_all(self):
        from core.mcp_client import MCPClientManager
        mgr = MCPClientManager()
        mgr.servers["myserver"] = {}
        asyncio.run(mgr.close_all())
        assert mgr.servers == {}


# ─── get_mcp_manager singleton ───────────────────────────────────────────────
class TestGetMCPManager:
    def test_singleton(self):
        import core.mcp_client as mod
        old = mod._manager
        try:
            mod._manager = None
            mgr1 = mod.get_mcp_manager()
            mgr2 = mod.get_mcp_manager()
            assert mgr1 is mgr2
        finally:
            mod._manager = old


# ─── MCPToolWrapper ──────────────────────────────────────────────────────────
class TestMCPToolWrapper:
    def _make_tool_info(self, name="test_tool", description="A test tool",
                        properties=None, required=None):
        info = MagicMock()
        info.name = name
        info.description = description
        schema = {}
        if properties:
            schema["properties"] = properties
        if required:
            schema["required"] = required
        info.inputSchema = schema
        return info

    def test_init_with_properties(self):
        from tools.mcp_tool import MCPToolWrapper
        info = self._make_tool_info(
            properties={"query": {"type": "string", "description": "Search query"}},
            required=["query"]
        )
        wrapper = MCPToolWrapper("myserver", info)
        assert wrapper.name == "mcp_myserver_test_tool"
        assert wrapper.requires_permission is True

    def test_init_without_properties(self):
        from tools.mcp_tool import MCPToolWrapper
        info = self._make_tool_info(properties=None)
        wrapper = MCPToolWrapper("myserver", info)
        assert wrapper.name == "mcp_myserver_test_tool"

    def test_init_no_description(self):
        from tools.mcp_tool import MCPToolWrapper
        info = self._make_tool_info(description=None, properties=None)
        wrapper = MCPToolWrapper("myserver", info)
        assert "MCP tool" in wrapper.description

    def test_init_optional_property(self):
        from tools.mcp_tool import MCPToolWrapper
        info = self._make_tool_info(
            properties={"limit": {"type": "integer", "description": "Max results"}},
            required=None
        )
        wrapper = MCPToolWrapper("myserver", info)
        assert wrapper is not None

    def test_execute_success(self):
        from tools.mcp_tool import MCPToolWrapper
        info = self._make_tool_info(properties={"q": {"type": "string"}})
        wrapper = MCPToolWrapper("myserver", info)

        mock_manager = MagicMock()
        mock_manager.call_tool = AsyncMock(return_value="tool result")

        with patch("tools.mcp_tool.get_mcp_manager", return_value=mock_manager):
            result = wrapper.execute(q="test")
            assert result == "tool result"

    def test_execute_new_event_loop(self):
        from tools.mcp_tool import MCPToolWrapper
        info = self._make_tool_info(properties=None)
        wrapper = MCPToolWrapper("myserver", info)

        mock_manager = MagicMock()
        mock_manager.call_tool = AsyncMock(return_value="result")

        with patch("tools.mcp_tool.get_mcp_manager", return_value=mock_manager), \
             patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            result = wrapper.execute()
            assert result == "result"
