"""Extended tests for core/chat.py — llamacpp path, error handling, self-reflection."""
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


# ─── _send_message_locked — llamacpp provider ─────────────────────────────────
class TestChatLlamacpp:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.llamacpp_provider.chat")
    def test_llamacpp_simple_response(self, mock_chat, mock_tools, mock_providers,
                                       mock_mem, mock_rag, mock_compact):
        mock_chat.return_value = MockResponse("llama response")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "llamacpp")
        state.config.set("model", "test.gguf")
        state.config.set("llamacpp_host", "http://localhost:8069")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        mock_chat.assert_called_once()
        asst_msgs = [m for m in state.messages if m["role"] == "assistant"]
        assert len(asst_msgs) >= 1

    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.llamacpp_provider.chat")
    def test_llamacpp_connection_error(self, mock_chat, mock_tools, mock_providers,
                                        mock_mem, mock_rag, mock_compact):
        mock_chat.side_effect = ConnectionError("Connection refused")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "llamacpp")
        state.config.set("model", "test.gguf")
        state.config.set("llamacpp_host", "http://localhost:8069")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        user_msgs = [m for m in state.messages if m["role"] == "user"]
        assert len(user_msgs) == 0


# ─── _send_message_locked — cloud provider ────────────────────────────────────
class TestChatCloud:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("llm.openai_provider.chat")
    def test_cloud_provider_simple(self, mock_chat, mock_tools, mock_rag, mock_mem, mock_compact):
        mock_chat.return_value = MockResponse("cloud response")

        cloud_providers = [{"name": "nvidia", "type": "cloud", "base_url": "https://api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY", "model": "nvidia/llama-3.1-nemotron-70b-instruct"}]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "nvidia")
        state.config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")
        state.config.set("self_reflection", False)

        with patch("core.chat.get_available_providers", return_value=cloud_providers):
            from core.chat import _send_message_locked
            _send_message_locked("hello")

        mock_chat.assert_called_once()
        asst_msgs = [m for m in state.messages if m["role"] == "assistant"]
        assert len(asst_msgs) >= 1

    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("llm.openai_provider.chat")
    def test_cloud_provider_tool_calls(self, mock_chat, mock_tools, mock_rag, mock_mem, mock_compact):
        tc = MockToolCall("read_file", {"path": "/tmp/test.txt"})
        mock_chat.return_value = MockResponse("", [tc])

        cloud_providers = [{"name": "nvidia", "type": "cloud", "base_url": "https://api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY", "model": "nvidia/llama-3.1-nemotron-70b-instruct"}]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "nvidia")
        state.config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")

        with patch("core.chat.get_available_providers", return_value=cloud_providers), \
             patch("core.chat.get_tool_by_name") as mock_get_tool:
            mock_tool = MockTool("read_file")
            mock_get_tool.return_value = mock_tool
            from core.chat import _send_message_locked
            _send_message_locked("read file")

        roles = [m["role"] for m in state.messages]
        assert "tool" in roles


class MockTool:
    def __init__(self, name="test_tool", requires_permission=False):
        self.name = name
        self.requires_permission = requires_permission

    def execute(self, **kwargs):
        return f"Executed {self.name}"


# ─── _send_message_locked — self_reflection retry ──────────────────────────────
class TestSelfReflectionRetry:
    @patch("core.chat._run_self_reflection", return_value=(False, "Need more detail"))
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_self_reflection_triggers_retry(self, mock_chat, mock_tools, mock_providers,
                                             mock_mem, mock_rag, mock_compact, mock_reflect):
        resp1 = MockResponse("First attempt")
        resp2 = MockResponse("Fixed attempt")
        mock_chat.side_effect = [resp1, resp2]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")
        state.config.set("self_reflection", True)

        from core.chat import _send_message_locked
        _send_message_locked("task")

        assert mock_chat.call_count == 2
        feedback_msgs = [m for m in state.messages if "Reviewer Feedback" in m.get("content", "")]
        assert len(feedback_msgs) >= 1


# ─── _send_message_locked — max iterations ────────────────────────────────────
class TestMaxIterations:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_reaches_max_iterations(self, mock_chat, mock_tools, mock_providers,
                                     mock_mem, mock_rag, mock_compact):
        tc = MockToolCall("execute_command", {"command": "echo test"})
        mock_chat.return_value = MockResponse("", [tc])

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")
        state.config.set("agent_max_iterations", 2)

        with patch("core.chat.get_tool_by_name") as mock_get_tool:
            mock_tool = MockTool("execute_command")
            mock_get_tool.return_value = mock_tool
            from core.chat import _send_message_locked
            _send_message_locked("loop task")

        assert mock_chat.call_count == 2


# ─── _send_message_locked — llamacpp error paths ──────────────────────────────
class TestErrorPaths:
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.llamacpp_provider.chat")
    def test_llamacpp_generic_error(self, mock_chat, mock_tools, mock_providers,
                                     mock_mem, mock_rag):
        mock_chat.side_effect = ValueError("Invalid model")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "llamacpp")
        state.config.set("model", "test.gguf")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        user_msgs = [m for m in state.messages if m["role"] == "user"]
        assert len(user_msgs) == 0

    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_ollama_connection_error(self, mock_chat, mock_tools, mock_providers,
                                      mock_mem, mock_rag):
        mock_chat.side_effect = ConnectionError("Connection refused")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        user_msgs = [m for m in state.messages if m["role"] == "user"]
        assert len(user_msgs) == 0

    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_ollama_model_not_found(self, mock_chat, mock_tools, mock_providers,
                                     mock_mem, mock_rag):
        mock_chat.side_effect = Exception("model not found: llama3")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "llama3")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        user_msgs = [m for m in state.messages if m["role"] == "user"]
        assert len(user_msgs) == 0

    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_generic_error(self, mock_chat, mock_tools, mock_providers,
                            mock_mem, mock_rag):
        mock_chat.side_effect = RuntimeError("Something weird")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        user_msgs = [m for m in state.messages if m["role"] == "user"]
        assert len(user_msgs) == 0
