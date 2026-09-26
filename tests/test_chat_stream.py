"""Tests for core/chat.py — streaming paths (_send_message_stream_locked)."""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class MockTool:
    def __init__(self, name="test_tool", requires_permission=False):
        self.name = name
        self.requires_permission = requires_permission
    def execute(self, **kwargs):
        return f"Executed {self.name}"


# ─── Streaming — command handling ─────────────────────────────────────────────
class TestStreamCommand:
    @patch("cli.commands.handle_command")
    def test_slash_command_yields_status_and_done(self, mock_cmd):
        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]

        from core.chat import _send_message_stream_locked
        events = list(_send_message_stream_locked("/help"))

        types = [e["type"] for e in events]
        assert "status" in types
        assert "done" in types
        mock_cmd.assert_called_once_with("/help")


# ─── Streaming — simple text response ────────────────────────────────────────
class TestStreamSimple:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.agent.ollama_provider.chat_stream")
    def test_yields_tokens_and_done(self, mock_stream, mock_tools, mock_providers,
                                     mock_mem, mock_rag, mock_compact):
        mock_stream.return_value = iter(["Hello", " World"])

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")
        state.config.set("self_reflection", False)

        from core.chat import _send_message_stream_locked
        events = list(_send_message_stream_locked("hi"))

        types = [e["type"] for e in events]
        assert "token" in types
        assert "done" in types

        token_events = [e for e in events if e["type"] == "token"]
        assert token_events[0]["content"] == "Hello"
        assert token_events[1]["content"] == " World"


# ─── Streaming — tool call ────────────────────────────────────────────────────
class TestStreamToolCall:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.agent.ollama_provider.chat_stream")
    def test_tool_call_yields_events(self, mock_stream, mock_tools, mock_providers,
                                      mock_mem, mock_rag, mock_compact):
        from llm.ollama_provider import ToolCallMarker
        mock_tc = MagicMock()
        mock_tc.id = "call_test123"
        mock_tc.function.name = "read_file"
        mock_tc.function.arguments = {"path": "/tmp/test.txt"}
        mock_msg = MagicMock()
        mock_msg.tool_calls = [mock_tc]
        mock_stream.return_value = iter([ToolCallMarker(mock_msg)])

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")
        state.config.set("self_reflection", False)

        with patch("core.chat.get_tool_by_name") as mock_get_tool:
            mock_tool = MockTool("read_file")
            mock_get_tool.return_value = mock_tool
            from core.chat import _send_message_stream_locked
            events = list(_send_message_stream_locked("read file"))

        types = [e["type"] for e in events]
        assert "tool_calls" in types
        assert "tool_result" in types
        assert "done" in types


# ─── Streaming — error path ───────────────────────────────────────────────────
class TestStreamError:
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.agent.ollama_provider.chat_stream")
    def test_error_yields_error_event(self, mock_stream, mock_tools, mock_providers,
                                       mock_mem, mock_rag):
        mock_stream.side_effect = Exception("Connection failed")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_stream_locked
        events = list(_send_message_stream_locked("hello"))

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "Connection failed" in error_events[0]["content"]


# ─── Streaming — llamacpp path ────────────────────────────────────────────────
class TestStreamLlamacpp:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.llamacpp_provider.chat_stream")
    def test_uses_llamacpp_stream(self, mock_stream, mock_tools, mock_providers,
                                   mock_mem, mock_rag, mock_compact):
        mock_stream.return_value = iter(["llama response"])

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "llamacpp")
        state.config.set("model", "test.gguf")
        state.config.set("llamacpp_host", "http://localhost:8069")
        state.config.set("self_reflection", False)

        from core.chat import _send_message_stream_locked
        events = list(_send_message_stream_locked("hello"))

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 1
        assert token_events[0]["content"] == "llama response"


# ─── Streaming — max iterations ──────────────────────────────────────────────
class TestStreamMaxIter:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.agent.ollama_provider.chat_stream")
    def test_max_iterations_event(self, mock_stream, mock_tools, mock_providers,
                                   mock_mem, mock_rag, mock_compact):
        from llm.ollama_provider import ToolCallMarker
        mock_tc = MagicMock()
        mock_tc.id = "c1"
        mock_tc.function.name = "execute_command"
        mock_tc.function.arguments = {"command": "echo test"}
        mock_msg = MagicMock()
        mock_msg.tool_calls = [mock_tc]
        mock_stream.return_value = iter([ToolCallMarker(mock_msg)])

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")
        state.config.set("agent_max_iterations", 2)

        with patch("core.chat.get_tool_by_name") as mock_get_tool:
            mock_tool = MockTool("execute_command")
            mock_get_tool.return_value = mock_tool
            from core.chat import _send_message_stream_locked
            events = list(_send_message_stream_locked("loop"))

        # Should have done event after tool execution
        types = [e["type"] for e in events]
        assert "done" in types
        tool_events = [e for e in events if e["type"] == "tool_result"]
        assert len(tool_events) >= 1
