"""Extended tests for core/agent.py — cloud provider, yield_func, memory storage."""
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


class MockTool:
    def __init__(self, name="test_tool", requires_permission=False):
        self.name = name
        self.requires_permission = requires_permission
    def execute(self, **kwargs):
        return f"Executed {self.name}"


# ─── Agent with yield_func (SSE/Web UI path) ─────────────────────────────────
class TestAgentYieldFunc:
    @patch("core.agent.ollama_provider")
    def test_yield_func_receives_events(self, mock_op):
        mock_op.chat.return_value = MockResponse("done")

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=3)

        # Simulate yield_func being set on thread_local
        from core.permissions import thread_local
        mock_yield = MagicMock()
        thread_local.yield_func = mock_yield

        try:
            with patch("core.agent.request_permission", return_value=True):
                result = agent.run("test task")

            # yield_func should have been called multiple times
            assert mock_yield.call_count >= 2
            # First call should be status about starting
            first_call = mock_yield.call_args_list[0]
            assert "Agent starting task" in first_call[0][0]["content"]
        finally:
            thread_local.yield_func = None

    @patch("core.agent.ollama_provider")
    def test_yield_error_on_llm_failure(self, mock_op):
        mock_op.chat.side_effect = Exception("Connection failed")

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=3)

        from core.permissions import thread_local
        mock_yield = MagicMock()
        thread_local.yield_func = mock_yield

        try:
            with patch("core.agent.request_permission", return_value=True):
                result = agent.run("test")

            error_calls = [c for c in mock_yield.call_args_list if c[0][0].get("type") == "error"]
            assert len(error_calls) >= 1
        finally:
            thread_local.yield_func = None


# ─── Agent tool call with yield ──────────────────────────────────────────────
class TestAgentToolCallYield:
    @patch("core.agent.ollama_provider")
    def test_tool_calls_yield_events(self, mock_op):
        tc = MockToolCall("read_file", {"path": "/tmp/test.txt"})
        resp1 = MockResponse("", [tc])
        resp2 = MockResponse("done")

        mock_op.chat.side_effect = [resp1, resp2]

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=5)

        from core.permissions import thread_local
        mock_yield = MagicMock()
        thread_local.yield_func = mock_yield

        try:
            with patch("core.agent.get_tool_by_name") as mock_get_tool, \
                 patch("core.agent.request_permission", return_value=True):
                mock_tool = MockTool("read_file")
                mock_get_tool.return_value = mock_tool
                result = agent.run("read file")

            # Should yield tool_calls and tool_result events
            event_types = [c[0][0].get("type") for c in mock_yield.call_args_list]
            assert "tool_calls" in event_types
            assert "tool_result" in event_types
        finally:
            thread_local.yield_func = None


# ─── Agent with cloud provider ────────────────────────────────────────────────
class TestAgentCloudProvider:
    @patch("llm.fallback.get_available_providers")
    @patch("core.agent.ollama_provider")
    def test_uses_cloud_provider(self, mock_op, mock_providers):
        from llm import openai_provider
        with patch.object(openai_provider, "chat", return_value=MockResponse("cloud answer")):
            mock_providers.return_value = [
                {"name": "nvidia", "type": "cloud", "base_url": "https://api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY", "model": "nvidia/llama-3.1-nemotron-70b-instruct"}
            ]

            from core.config import Config
            from core.agent import ReActAgent
            config = Config()
            config.set("provider", "nvidia")
            config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")
            config.set("enable_reflection", False)
            agent = ReActAgent(config, max_iterations=3)

            with patch("core.agent.request_permission", return_value=True):
                result = agent.run("test")

            assert result == "cloud answer"
            # chat called once for response (reflection disabled)
            assert openai_provider.chat.call_count == 1


# ─── Agent memory storage ─────────────────────────────────────────────────────
class TestAgentMemoryStorage:
    @patch("core.agent.ollama_provider")
    @patch("core.memory.store_memory")
    def test_stores_task_in_memory(self, mock_store, mock_op):
        mock_op.chat.return_value = MockResponse("Task completed")

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=3)

        with patch("core.agent.request_permission", return_value=True):
            agent.run("Create a test file")

        mock_store.assert_called_once()
        call_args = mock_store.call_args
        assert "task_" in call_args[1]["key"]


# ─── Agent max iterations with yield ──────────────────────────────────────────
class TestAgentMaxIterYield:
    @patch("core.agent.ollama_provider")
    def test_max_iterations_yields_status(self, mock_op):
        tc = MockToolCall("execute_command", {"command": "echo test"})
        mock_op.chat.return_value = MockResponse("", [tc])

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=2)

        from core.permissions import thread_local
        mock_yield = MagicMock()
        thread_local.yield_func = mock_yield

        try:
            with patch("core.agent.get_tool_by_name") as mock_get_tool, \
                 patch("core.agent.request_permission", return_value=True):
                mock_tool = MockTool("execute_command")
                mock_get_tool.return_value = mock_tool
                result = agent.run("loop task")

            # Should yield max iterations status
            event_types = [c[0][0].get("type") for c in mock_yield.call_args_list]
            # The agent should complete (tool returns, then final text)
            assert "done" in event_types or "status" in event_types
        finally:
            thread_local.yield_func = None


# ─── Agent with tool call ID generation ───────────────────────────────────────
class TestAgentToolCallID:
    @patch("core.agent.ollama_provider")
    def test_tool_call_without_id_gets_generated(self, mock_op):
        tc = MockToolCall("read_file", {"path": "/tmp/test.txt"})
        tc.id = None  # No ID
        resp1 = MockResponse("", [tc])
        resp2 = MockResponse("done")
        mock_op.chat.side_effect = [resp1, resp2]

        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        config.set("provider", "ollama")
        agent = ReActAgent(config, max_iterations=5)

        with patch("core.agent.get_tool_by_name") as mock_get_tool, \
             patch("core.agent.request_permission", return_value=True):
            mock_tool = MockTool("read_file")
            mock_get_tool.return_value = mock_tool
            agent.run("test")

        # Tool call should have been assigned an ID
        assert tc.id is not None
        assert tc.id.startswith("call_")


# ─── Agent _execute_tool with config/depth ────────────────────────────────────
class TestAgentExecuteToolExtraArgs:
    def test_tool_receives_config_and_depth(self):
        from core.config import Config
        from core.agent import ReActAgent
        config = Config()
        agent = ReActAgent(config, depth=1)

        # Create a tool that accepts config and depth
        class ToolWithConfig:
            name = "test_tool"
            requires_permission = False
            def execute(self, config=None, depth=None, **kwargs):
                return f"config={type(config).__name__}, depth={depth}"

        with patch("core.agent.get_tool_by_name") as mock_get_tool:
            mock_get_tool.return_value = ToolWithConfig()
            tc = MockToolCall("test_tool", {})
            result = agent._execute_tool(tc)
            assert "config=Config" in result
            assert "depth=1" in result


# ─── Context: tiktoken path ──────────────────────────────────────────────────
class TestContextTiktoken:
    def test_fallback_when_no_tiktoken(self):
        """estimate_messages_tokens falls back to char-based estimate."""
        from core.context import estimate_messages_tokens
        messages = [{"role": "user", "content": "hello world test"}]
        tokens = estimate_messages_tokens(messages)
        # Should be positive and reasonable
        assert tokens > 0

    def test_with_tool_calls_fallback(self):
        """Fallback handles tool_calls in messages."""
        from core.context import estimate_messages_tokens
        messages = [
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "read_file", "arguments": "{}"}}
            ]}
        ]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0

    def test_with_unserializable_tool_calls(self):
        """Fallback handles unserializable tool_calls."""
        from core.context import estimate_messages_tokens
        # Create a tool_calls with an unserializable object
        messages = [
            {"role": "assistant", "content": "", "tool_calls": "not a list"}
        ]
        # This should not crash - the json.dumps should fail gracefully
        # Actually, the code checks `if "tool_calls" in m and m["tool_calls"]`
        # If tool_calls is a string, it's truthy, so json.dumps will be called on a string
        # which will fail. But the try/except catches it.
        tokens = estimate_messages_tokens(messages)
        assert tokens >= 0


# ─── Context: compact_context with tool_calls in history ──────────────────────
class TestContextToolCallsInHistory:
    @patch("core.context.call_active_llm")
    def test_tool_calls_in_old_messages(self, mock_llm):
        mock_llm.return_value = "Summary of tool usage."

        from core.context import compact_context
        from core.config import Config
        config = Config()

        messages = [{"role": "system", "content": "prompt"}]
        # Add messages with tool_calls
        for i in range(25):
            if i % 3 == 0:
                messages.append({"role": "assistant", "content": "", "tool_calls": [
                    {"function": {"name": "read_file", "arguments": "{}"}}
                ]})
            else:
                messages.append({"role": "user", "content": f"message {i}" * 50})

        result = compact_context(messages, config)

        # Should have summary + recent messages
        assert len(result) >= 3
        # Summary should mention tools
        summary = [m for m in result if "Summary" in m.get("content", "")]
        assert len(summary) == 1
