"""Tests for core/agent.py — extended ReAct agent coverage."""
import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class MockResponse:
    def __init__(self, content="", tool_calls=None):
        self.message = MagicMock()
        self.message.content = content
        self.message.tool_calls = tool_calls or []


class MockToolCall:
    def __init__(self, name, arguments):
        self.id = f"call_{uuid.uuid4().hex[:8]}"
        self.function = MagicMock()
        self.function.name = name
        self.function.arguments = arguments


# ─── ReActAgent initialization ────────────────────────────────────────────────
class TestAgentInit:
    def test_init_ollama(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config)
        assert agent.provider == "ollama"
        assert agent.host == "http://localhost:11434"
        assert agent.depth == 0

    def test_init_llamacpp(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "llamacpp")
        config.set("llamacpp_host", "http://localhost:8069")
        agent = ReActAgent(config)
        assert agent.provider == "llamacpp"
        assert agent.host == "http://localhost:8069"

    def test_init_with_depth(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config, depth=2)
        assert agent.depth == 2

    def test_init_with_custom_max_iterations(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config, max_iterations=5)
        assert agent.max_iterations == 5

    def test_init_sets_system_prompt(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config)
        assert len(agent.messages) == 1
        assert agent.messages[0]["role"] == "system"
        assert "Chatty Chronos" in agent.messages[0]["content"]


# ─── ReActAgent.run — simple text response ────────────────────────────────────
class TestAgentRunSimple:
    @patch("core.agent.ollama_provider")
    def test_simple_text_response(self, mock_op):
        mock_op.chat.return_value = MockResponse("Task completed.")

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=5)

        with patch("core.agent.request_permission", return_value=True):
            result = agent.run("Do something simple")

        assert result == "Task completed."

    @patch("core.agent.ollama_provider")
    def test_empty_response(self, mock_op):
        mock_op.chat.return_value = MockResponse("")

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=5)

        with patch("core.agent.request_permission", return_value=True):
            result = agent.run("Task")

        assert result == ""


# ─── ReActAgent.run — tool call flow ──────────────────────────────────────────
class TestAgentToolCalls:
    @patch("core.agent.ollama_provider")
    def test_tool_call_flow(self, mock_op):
        tc = MockToolCall("read_file", {"path": "/tmp/test.txt"})
        resp1 = MockResponse("", [tc])
        resp2 = MockResponse("File contains test data.")

        mock_op.chat.side_effect = [resp1, resp2]

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=5)

        with patch("core.agent.get_tool_by_name") as mock_get_tool, \
             patch("core.agent.request_permission", return_value=True):
            mock_tool = MagicMock()
            mock_tool.requires_permission = False
            mock_tool.execute.return_value = "file contents here"
            mock_get_tool.return_value = mock_tool

            result = agent.run("Read the file")

        assert result == "File contains test data."

    @patch("core.agent.ollama_provider")
    def test_max_iterations_reached(self, mock_op):
        tc = MockToolCall("execute_command", {"command": "echo test"})
        mock_op.chat.return_value = MockResponse("", [tc])

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=3)

        with patch("core.agent.get_tool_by_name") as mock_get_tool, \
             patch("core.agent.request_permission", return_value=True):
            mock_tool = MagicMock()
            mock_tool.requires_permission = False
            mock_tool.execute.return_value = "done"
            mock_get_tool.return_value = mock_tool

            result = agent.run("Infinite task")

        assert "maximum iterations" in result.lower()

    @patch("core.agent.ollama_provider")
    def test_llm_error_returns_failure(self, mock_op):
        mock_op.chat.side_effect = Exception("Connection refused")

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=5)

        result = agent.run("Task")
        assert "Agent failed" in result

    @patch("core.agent.ollama_provider")
    def test_permission_denied_returns_error(self, mock_op):
        tc = MockToolCall("write_file", {"path": "/tmp/test.txt", "content": "data"})
        mock_op.chat.return_value = MockResponse("", [tc])

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=5)

        with patch("core.agent.get_tool_by_name") as mock_get_tool, \
             patch("core.agent.request_permission", return_value=False):
            mock_tool = MagicMock()
            mock_tool.requires_permission = True
            mock_get_tool.return_value = mock_tool

            result = agent.run("Write a file")

        assert isinstance(result, str)


# ─── ReActAgent._execute_tool ─────────────────────────────────────────────────
class TestAgentExecuteTool:
    def test_unknown_tool(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config)

        tc = MockToolCall("nonexistent_tool", {})
        result = agent._execute_tool(tc)
        assert "Unknown tool" in result

    def test_permission_denied(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config)

        with patch("core.agent.get_tool_by_name") as mock_get_tool, \
             patch("core.agent.request_permission", return_value=False):
            mock_tool = MagicMock()
            mock_tool.requires_permission = True
            mock_get_tool.return_value = mock_tool

            tc = MockToolCall("write_file", {"path": "/tmp/test.txt"})
            result = agent._execute_tool(tc)
            assert "Permission denied" in result

    def test_tool_executes(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config)

        with patch("core.agent.get_tool_by_name") as mock_get_tool, \
             patch("core.agent.request_permission", return_value=True):
            mock_tool = MagicMock()
            mock_tool.requires_permission = False
            mock_tool.execute.return_value = "Tool result"
            mock_get_tool.return_value = mock_tool

            tc = MockToolCall("read_file", {"path": "/tmp/test.txt"})
            result = agent._execute_tool(tc)
            assert result == "Tool result"

    def test_diff_generated_for_write_file(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config)

        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("old content")
            tmp_path = f.name

        try:
            with patch("core.agent.get_tool_by_name") as mock_get_tool, \
                 patch("core.agent.request_permission") as mock_perm:
                mock_tool = MagicMock()
                mock_tool.requires_permission = True
                mock_get_tool.return_value = mock_tool
                mock_perm.return_value = True

                tc = MockToolCall("write_file", {"path": tmp_path, "content": "new content"})
                agent._execute_tool(tc)

                call_args = mock_perm.call_args
                assert call_args[1].get("diff_text") is not None or call_args[0][2] is not None
        finally:
            os.unlink(tmp_path)

    def test_diff_generated_for_search_replace(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config)

        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("apple banana apple")
            tmp_path = f.name

        try:
            with patch("core.agent.get_tool_by_name") as mock_get_tool, \
                 patch("core.agent.request_permission") as mock_perm:
                mock_tool = MagicMock()
                mock_tool.requires_permission = True
                mock_get_tool.return_value = mock_tool
                mock_perm.return_value = True

                tc = MockToolCall("search_replace", {"path": tmp_path, "search": "apple", "replace": "orange"})
                agent._execute_tool(tc)

                call_args = mock_perm.call_args
                assert call_args[1].get("diff_text") is not None or call_args[0][2] is not None
        finally:
            os.unlink(tmp_path)


# Provider path tests are covered by TestAgentInit and the existing test_agent.py
