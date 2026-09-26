"""Tests for core/chat.py — message handling, tool execution, self-reflection."""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── Helpers ──────────────────────────────────────────────────────────────────
class MockResponse:
    def __init__(self, content="", tool_calls=None):
        self.message = MagicMock()
        self.message.content = content
        self.message.tool_calls = tool_calls or []


class MockToolCall:
    def __init__(self, name, arguments, tc_id=None):
        self.id = tc_id or f"call_{uuid.uuid4().hex[:8]}"
        self.function = MagicMock()
        self.function.name = name
        self.function.arguments = arguments


class MockTool:
    def __init__(self, name="test_tool", requires_permission=False):
        self.name = name
        self.requires_permission = requires_permission

    def execute(self, **kwargs):
        return f"Executed {self.name} with {kwargs}"


# ─── execute_tool_call ────────────────────────────────────────────────────────
class TestExecuteToolCall:
    @patch("core.chat.get_tool_by_name")
    def test_unknown_tool_returns_error(self, mock_get_tool):
        mock_get_tool.return_value = None
        tc = MockToolCall("nonexistent_tool", {})

        from core.chat import execute_tool_call
        result = execute_tool_call(tc)

        assert "Error: Unknown tool" in result
        assert "nonexistent_tool" in result

    @patch("core.chat.get_tool_by_name")
    def test_known_tool_executes_without_permission(self, mock_get_tool):
        mock_tool = MockTool("read_file", requires_permission=False)
        mock_get_tool.return_value = mock_tool
        tc = MockToolCall("read_file", {"path": "/tmp/test.txt"})

        from core.chat import execute_tool_call
        result = execute_tool_call(tc)

        assert "Executed read_file" in result

    @patch("core.chat.get_tool_by_name")
    @patch("core.chat.request_permission", return_value=False)
    def test_permission_denied(self, mock_perm, mock_get_tool):
        mock_tool = MockTool("write_file", requires_permission=True)
        mock_get_tool.return_value = mock_tool
        tc = MockToolCall("write_file", {"path": "/tmp/test.txt", "content": "hello"})

        from core.chat import execute_tool_call
        result = execute_tool_call(tc)

        assert "Permission denied" in result

    @patch("core.chat.get_tool_by_name")
    @patch("core.chat.request_permission", return_value=True)
    def test_permission_granted(self, mock_perm, mock_get_tool):
        mock_tool = MockTool("write_file", requires_permission=True)
        mock_get_tool.return_value = mock_tool
        tc = MockToolCall("write_file", {"path": "/tmp/test.txt", "content": "hello"})

        from core.chat import execute_tool_call
        result = execute_tool_call(tc)

        assert "Executed write_file" in result
        mock_perm.assert_called_once()

    @patch("core.chat.get_tool_by_name")
    def test_no_permission_needed_skips_check(self, mock_get_tool):
        mock_tool = MockTool("grep", requires_permission=False)
        mock_get_tool.return_value = mock_tool
        tc = MockToolCall("grep", {"pattern": "TODO", "path": "."})

        from core.chat import execute_tool_call
        with patch("core.chat.request_permission") as mock_perm:
            result = execute_tool_call(tc)
            mock_perm.assert_not_called()

        assert "Executed grep" in result


# ─── _send_message_locked (simple text response) ──────────────────────────────
class TestSendMessageLocked:
    @patch("core.chat.compact_context")
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_simple_text_response(self, mock_chat, mock_tools, mock_providers,
                                   mock_mem, mock_rag, mock_compact):
        mock_chat.return_value = MockResponse("Hello! I can help you.")
        mock_compact.return_value = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello! I can help you."},
        ]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_locked
        _send_message_locked("hi")

        user_msgs = [m for m in state.messages if m["role"] == "user"]
        assert len(user_msgs) >= 1

        asst_msgs = [m for m in state.messages if m["role"] == "assistant"]
        assert len(asst_msgs) >= 1
        assert asst_msgs[-1]["content"] == "Hello! I can help you."

    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_tool_call_flow(self, mock_chat, mock_tools, mock_providers,
                            mock_mem, mock_rag, mock_compact):
        tc = MockToolCall("read_file", {"path": "/tmp/test.txt"})
        resp1 = MockResponse("", [tc])
        resp2 = MockResponse("The file contains test data.")

        mock_chat.side_effect = [resp1, resp2]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        with patch("core.chat.get_tool_by_name") as mock_get_tool:
            mock_tool = MockTool("read_file")
            mock_get_tool.return_value = mock_tool
            from core.chat import _send_message_locked
            _send_message_locked("read the file")

        roles = [m["role"] for m in state.messages]
        assert "tool" in roles

    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value="RAG context here")
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_rag_context_injected(self, mock_chat, mock_tools, mock_providers,
                                   mock_mem, mock_rag, mock_compact):
        mock_chat.return_value = MockResponse("Based on the docs...")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_locked
        _send_message_locked("question")

        # Verify RAG was queried
        mock_rag.assert_called_once_with("question", config=state.config)

    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_error_handling_connection(self, mock_chat, mock_tools, mock_providers,
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
    @patch("core.chat.llamacpp_provider.chat")
    def test_llamacpp_provider_used(self, mock_chat, mock_tools, mock_providers,
                                     mock_mem, mock_rag):
        mock_chat.return_value = MockResponse("Response from llama.cpp")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "llamacpp")
        state.config.set("model", "test.gguf")
        state.config.set("llamacpp_host", "http://localhost:8069")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        mock_chat.assert_called_once()

    @patch("core.chat.compact_context")
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_empty_response_prints_success(self, mock_chat, mock_tools, mock_providers,
                                            mock_mem, mock_rag, mock_compact):
        mock_chat.return_value = MockResponse("")
        mock_compact.return_value = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": ""},
        ]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        asst_msgs = [m for m in state.messages if m["role"] == "assistant"]
        assert len(asst_msgs) >= 1


# ─── _run_self_reflection ─────────────────────────────────────────────────────
class TestSelfReflection:
    @patch("core.chat.ollama_provider.chat_stream")
    def test_yes_response(self, mock_stream):
        mock_stream.return_value = iter(["YES"])

        from core.chat import _run_self_reflection
        is_ok, feedback = _run_self_reflection("test", "response", "ollama", "model", "host", None)

        assert is_ok is True
        assert feedback == ""

    @patch("core.chat.ollama_provider.chat_stream")
    def test_no_response(self, mock_stream):
        mock_stream.return_value = iter(["NO: Missing error handling"])

        from core.chat import _run_self_reflection
        is_ok, feedback = _run_self_reflection("test", "response", "ollama", "model", "host", None)

        assert is_ok is False
        assert "Missing error handling" in feedback

    @patch("core.chat.ollama_provider.chat_stream")
    def test_exception_returns_ok(self, mock_stream):
        mock_stream.side_effect = Exception("Connection failed")

        from core.chat import _run_self_reflection
        is_ok, feedback = _run_self_reflection("test", "response", "ollama", "model", "host", None)

        assert is_ok is True
        assert feedback == ""

    @patch("llm.openai_provider.chat")
    def test_cloud_provider_reflection(self, mock_chat):
        """Self-reflection works with cloud providers."""
        mock_response = MagicMock()
        mock_response.message.content = "YES"
        mock_chat.return_value = mock_response

        cloud_provider = {"name": "nvidia", "type": "cloud", "base_url": "https://api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY"}

        from core import state
        state.config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")

        from core.chat import _run_self_reflection
        is_ok, feedback = _run_self_reflection("test", "response", "nvidia", "model", "host", cloud_provider)

        assert is_ok is True
        mock_chat.assert_called_once()

    @patch("core.chat.llamacpp_provider.chat_stream")
    def test_llamacpp_reflection(self, mock_stream):
        """Self-reflection works with llama.cpp."""
        mock_stream.return_value = iter(["YES"])

        from core.chat import _run_self_reflection
        is_ok, feedback = _run_self_reflection("test", "response", "llamacpp", "model", "http://localhost:8069", None)

        assert is_ok is True
        mock_stream.assert_called_once()


# ─── execute_tool_call — extra paths ──────────────────────────────────────────
class TestExecuteToolCallExtended:
    @patch("core.chat.get_tool_by_name")
    def test_tool_with_get_diff(self, mock_get_tool):
        """Tool with get_diff method gets diff_text passed to permission."""
        class ToolWithDiff:
            name = "write_file"
            requires_permission = True
            def execute(self, **kwargs): return "ok"
            def get_diff(self, **kwargs): return "- old\n+ new"

        mock_get_tool.return_value = ToolWithDiff()
        tc = MockToolCall("write_file", {"path": "/tmp/test.txt", "content": "hello"})

        from core.chat import execute_tool_call
        with patch("core.chat.request_permission", return_value=True) as mock_perm:
            result = execute_tool_call(tc)
            # Check diff_text was passed
            call_args = mock_perm.call_args
            assert call_args[1].get("diff_text") == "- old\n+ new" or call_args[0][2] == "- old\n+ new"

    @patch("core.chat.get_tool_by_name")
    def test_tool_with_config_parameter(self, mock_get_tool):
        """Tool that accepts config parameter gets it injected."""
        class ToolWithConfig:
            name = "test_tool"
            requires_permission = False
            def execute(self, config=None, **kwargs):
                return f"config_type={type(config).__name__}"

        mock_get_tool.return_value = ToolWithConfig()
        tc = MockToolCall("test_tool", {})

        from core.chat import execute_tool_call
        result = execute_tool_call(tc)
        assert "config_type=Config" in result


# ─── _send_message_locked — cloud provider path ───────────────────────────────
class TestSendMessageCloud:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("llm.openai_provider.chat")
    def test_cloud_provider_chat(self, mock_chat, mock_tools, mock_rag, mock_mem, mock_compact):
        """Cloud provider (non-ollama) uses openai_provider.chat."""
        mock_response = MockResponse("Cloud response here")
        mock_chat.return_value = mock_response

        cloud_providers = [{"name": "nvidia", "type": "cloud", "base_url": "https://api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY", "model": "nvidia/llama-3.1-nemotron-70b-instruct"}]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "nvidia")
        state.config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")
        state.config.set("self_reflection", False)

        with patch("core.chat.get_available_providers", return_value=cloud_providers):
            from core.chat import _send_message_locked
            _send_message_locked("hello cloud")

        mock_chat.assert_called_once()
        asst_msgs = [m for m in state.messages if m["role"] == "assistant"]
        assert len(asst_msgs) >= 1

    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("llm.openai_provider.chat")
    def test_cloud_provider_tool_calls(self, mock_chat, mock_tools, mock_rag, mock_mem, mock_compact):
        """Cloud provider with tool calls executes them."""
        tc = MockToolCall("read_file", {"path": "/tmp/test.txt"})
        mock_response = MockResponse("", [tc])
        mock_chat.return_value = mock_response

        cloud_providers = [{"name": "nvidia", "type": "cloud", "base_url": "https://api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY", "model": "nvidia/llama-3.1-nemotron-70b-instruct"}]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "nvidia")
        state.config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")
        state.config.set("self_reflection", False)

        with patch("core.chat.get_available_providers", return_value=cloud_providers):
            with patch("core.chat.get_tool_by_name") as mock_get_tool:
                mock_tool = MockTool("read_file")
                mock_get_tool.return_value = mock_tool
                from core.chat import _send_message_locked
                _send_message_locked("read file")

        roles = [m["role"] for m in state.messages]
        assert "tool" in roles


# ─── _send_message_locked — memory injection ──────────────────────────────────
class TestMemoryInjection:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory")
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_memory_context_injected(self, mock_chat, mock_tools, mock_providers,
                                      mock_mem_search, mock_rag, mock_compact):
        """Past memory experiences are injected into system prompt."""
        captured_system = []
        def capture_chat(*args, **kwargs):
            # Capture system prompt during execution (before finally resets it)
            captured_system.append(state.messages[0]["content"])
            return MockResponse("Got it!")

        mock_chat.side_effect = capture_chat
        mock_mem_search.return_value = [
            {"content": "User prefers dark theme"},
            {"content": "Project uses pytest"},
        ]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_locked
        _send_message_locked("what testing framework?")

        # System prompt should include memory (captured during execution)
        assert len(captured_system) == 1
        sys_content = captured_system[0]
        assert "dark theme" in sys_content
        assert "pytest" in sys_content

    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_no_memory_no_injection(self, mock_chat, mock_tools, mock_providers,
                                     mock_mem_search, mock_rag, mock_compact):
        """When no memory, system prompt has no memory content injected."""
        captured_system = []
        def capture_chat(*args, **kwargs):
            captured_system.append(state.messages[0]["content"])
            return MockResponse("OK")

        mock_chat.side_effect = capture_chat

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        # System prompt should NOT contain memory markers
        assert len(captured_system) == 1
        assert "Past relevant context from Memory" not in captured_system[0]


# ─── _send_message_locked — self_reflection ───────────────────────────────────
class TestSelfReflectionInChat:
    @patch("core.chat._run_self_reflection", return_value=(False, "Needs more detail"))
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_self_reflection_retries(self, mock_chat, mock_tools, mock_providers,
                                      mock_mem, mock_rag, mock_compact, mock_reflect):
        """When self_reflection is enabled and fails, agent retries."""
        resp1 = MockResponse("First attempt")
        resp2 = MockResponse("Second attempt with fix")
        mock_chat.side_effect = [resp1, resp2]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")
        state.config.set("self_reflection", True)

        from core.chat import _send_message_locked
        _send_message_locked("task")

        # Should have been called twice (retry after reflection)
        assert mock_chat.call_count == 2
        # Feedback message should be in history
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
    def test_max_iterations_reached(self, mock_chat, mock_tools, mock_providers,
                                     mock_mem, mock_rag, mock_compact):
        """Agent stops after max_iterations."""
        tc = MockToolCall("execute_command", {"command": "echo test"})
        # Always return tool calls so it never reaches a text response
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
            _send_message_locked("infinite loop task")

        # Should have been called exactly 2 times (max_iterations)
        assert mock_chat.call_count == 2


# ─── _send_message_locked — error paths ───────────────────────────────────────
class TestErrorPaths:
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.llamacpp_provider.chat")
    def test_llamacpp_connection_error(self, mock_chat, mock_tools, mock_providers,
                                        mock_mem, mock_rag):
        """llamacpp connection error shows helpful message."""
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

    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_ollama_model_not_found(self, mock_chat, mock_tools, mock_providers,
                                     mock_mem, mock_rag):
        """Ollama 404 error shows model not found message."""
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
    def test_ollama_connection_refused(self, mock_chat, mock_tools, mock_providers,
                                        mock_mem, mock_rag):
        """Ollama connection refused shows helpful message."""
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
    def test_generic_error(self, mock_chat, mock_tools, mock_providers,
                            mock_mem, mock_rag):
        """Generic error shows error message."""
        mock_chat.side_effect = ValueError("Something went wrong")

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        from core.chat import _send_message_locked
        _send_message_locked("hello")

        user_msgs = [m for m in state.messages if m["role"] == "user"]
        assert len(user_msgs) == 0


# ─── _send_message_locked — tool_call id generation ───────────────────────────
class TestToolCallId:
    @patch("core.chat.compact_context", side_effect=lambda msgs, cfg: msgs)
    @patch("core.chat.get_rag_context", return_value=None)
    @patch("core.memory.search_memory", return_value=[])
    @patch("core.chat.get_available_providers", return_value=[])
    @patch("core.chat.get_ollama_tools_schema", return_value=[])
    @patch("core.chat.ollama_provider.chat")
    def test_tool_call_without_id_gets_generated(self, mock_chat, mock_tools,
                                                  mock_providers, mock_mem,
                                                  mock_rag, mock_compact):
        """Tool calls without id get a generated id."""
        tc = MockToolCall("read_file", {"path": "/tmp/test.txt"}, tc_id=None)
        tc.id = None  # Ensure no id
        resp1 = MockResponse("", [tc])
        resp2 = MockResponse("Done")
        mock_chat.side_effect = [resp1, resp2]

        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]
        state.config.set("provider", "ollama")
        state.config.set("model", "test-model")

        with patch("core.chat.get_tool_by_name") as mock_get_tool:
            mock_tool = MockTool("read_file")
            mock_get_tool.return_value = mock_tool
            from core.chat import _send_message_locked
            _send_message_locked("test")

        # Tool message should have a generated tool_call_id
        tool_msgs = [m for m in state.messages if m["role"] == "tool"]
        assert len(tool_msgs) >= 1
        assert tool_msgs[0].get("tool_call_id") is not None
