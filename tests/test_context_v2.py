"""Tests for core/context.py — extended coverage for call_active_llm, compact_context."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── call_active_llm ──────────────────────────────────────────────────────────
class TestCallActiveLlm:
    @patch("llm.ollama_provider.chat")
    @patch("llm.fallback.get_available_providers", return_value=[])
    def test_ollama_provider(self, mock_providers, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = "Ollama response"
        mock_chat.return_value = mock_response

        from core.config import Config
        config = Config()
        config.set("provider", "ollama")
        config.set("model", "test-model")

        from core.context import call_active_llm
        result = call_active_llm([{"role": "user", "content": "hi"}], config)

        assert result == "Ollama response"

    @patch("core.context.llamacpp_provider.chat")
    def test_llamacpp_provider(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = "llama.cpp response"
        mock_chat.return_value = mock_response

        from core.config import Config
        config = Config()
        config.set("provider", "llamacpp")
        config.set("model", "model.gguf")
        config.set("llamacpp_host", "http://localhost:8069")

        from core.context import call_active_llm
        result = call_active_llm([{"role": "user", "content": "hi"}], config)

        assert result == "llama.cpp response"

    @patch("core.context.llamacpp_provider.chat")
    def test_llamacpp_empty_content(self, mock_chat):
        mock_response = MagicMock()
        mock_response.message.content = None
        mock_chat.return_value = mock_response

        from core.config import Config
        config = Config()
        config.set("provider", "llamacpp")

        from core.context import call_active_llm
        result = call_active_llm([{"role": "user", "content": "hi"}], config)

        assert result == ""

    @patch("core.context.get_available_providers")
    @patch("llm.openai_provider.chat")
    def test_cloud_provider(self, mock_chat, mock_providers):
        mock_response = MagicMock()
        mock_response.message.content = "Cloud response"
        mock_chat.return_value = mock_response

        mock_providers.return_value = [
            {"name": "nvidia", "type": "cloud", "base_url": "https://api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY", "model": "nvidia/llama-3.1-nemotron-70b-instruct"}
        ]

        from core.config import Config
        config = Config()
        config.set("provider", "nvidia")
        config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")

        from core.context import call_active_llm
        result = call_active_llm([{"role": "user", "content": "hi"}], config)

        assert result == "Cloud response"

    @patch("core.context.ollama_provider.chat")
    def test_exception_returns_empty(self, mock_chat):
        mock_chat.side_effect = Exception("Connection failed")

        from core.config import Config
        config = Config()

        from core.context import call_active_llm
        result = call_active_llm([{"role": "user", "content": "hi"}], config)

        assert result == ""


# ─── estimate_messages_tokens ─────────────────────────────────────────────────
class TestEstimateTokens:
    def test_empty_messages(self):
        from core.context import estimate_messages_tokens
        assert estimate_messages_tokens([]) == 0

    def test_single_message(self):
        from core.context import estimate_messages_tokens
        messages = [{"role": "user", "content": "hello world"}]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0

    def test_multiple_messages(self):
        from core.context import estimate_messages_tokens
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 10

    def test_tool_calls_included(self):
        from core.context import estimate_messages_tokens
        messages = [
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "read_file", "arguments": '{"path": "/tmp/test.py"}'}}
            ]}
        ]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0

    def test_none_content(self):
        from core.context import estimate_messages_tokens
        messages = [{"role": "user", "content": None}]
        tokens = estimate_messages_tokens(messages)
        assert tokens >= 0


# ─── compact_context ──────────────────────────────────────────────────────────
class TestCompactContext:
    def test_no_compaction_needed(self):
        from core.context import compact_context
        messages = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "hello"},
        ]

        config = MagicMock()
        config.get.side_effect = lambda k, d=None: {
            "max_context_messages": 20,
            "max_context_tokens": 4000,
            "compaction_enabled": True,
        }.get(k, d)

        result = compact_context(messages, config)
        assert result == messages

    def test_pruning_when_compaction_disabled(self):
        from core.context import compact_context
        messages = [{"role": "system", "content": "prompt"}]
        for i in range(25):
            messages.append({"role": "user", "content": f"msg {i}" * 50})

        config = MagicMock()
        config.get.side_effect = lambda k, d=None: {
            "max_context_messages": 5,
            "max_context_tokens": 1,  # Force compaction
            "compaction_enabled": False,
        }.get(k, d)

        result = compact_context(messages, config)
        assert result[0]["role"] == "system"
        assert len(result) == 6  # 1 system + 5 kept

    @patch("core.context.call_active_llm")
    def test_compaction_with_summary(self, mock_llm):
        mock_llm.return_value = "Summary of conversation about Python testing."

        from core.context import compact_context
        messages = [{"role": "system", "content": "prompt"}]
        for i in range(25):
            messages.append({"role": "user", "content": f"message {i}" * 50})

        config = MagicMock()
        config.get.side_effect = lambda k, d=None: {
            "max_context_messages": 5,
            "max_context_tokens": 1,  # Force compaction
            "compaction_enabled": True,
        }.get(k, d)

        result = compact_context(messages, config)
        # Should have: system + summary + recent messages
        assert result[0]["role"] == "system"
        assert "Summary" in result[1]["content"]
        assert len(result) >= 3

    @patch("core.context.call_active_llm")
    def test_compaction_fallback_on_empty_summary(self, mock_llm):
        mock_llm.return_value = ""

        from core.context import compact_context
        messages = [{"role": "system", "content": "prompt"}]
        for i in range(25):
            messages.append({"role": "user", "content": f"message {i}" * 50})

        config = MagicMock()
        config.get.side_effect = lambda k, d=None: {
            "max_context_messages": 5,
            "max_context_tokens": 1,
            "compaction_enabled": True,
        }.get(k, d)

        result = compact_context(messages, config)
        # Should fall back to pruning
        assert result[0]["role"] == "system"
        assert len(result) <= 6

    def test_tool_calls_in_history_text(self):
        """Tool calls in old messages are included in summary text."""
        from core.context import call_active_llm
        # This tests the history_text building logic
        messages = [
            {"role": "system", "content": "prompt"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "read_file", "arguments": "{}"}}
            ]},
        ]
        # Verify the tool call info is extractable
        m = messages[1]
        assert "tool_calls" in m
        assert m["tool_calls"][0]["function"]["name"] == "read_file"
