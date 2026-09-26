"""Tests for core/context.py — token estimation and context compaction."""
import pytest
from unittest.mock import patch, MagicMock
from core.context import estimate_messages_tokens, compact_context


class TestEstimateMessagesTokens:
    def test_empty_messages(self):
        assert estimate_messages_tokens([]) == 0

    def test_single_system_message(self):
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0
        assert tokens < 50  # Short message should be small

    def test_multiple_messages(self):
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 10

    def test_message_with_tool_calls(self):
        messages = [
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "read_file", "arguments": {"path": "/tmp/test.py"}}}
            ]}
        ]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0

    def test_message_with_none_content(self):
        messages = [{"role": "user", "content": None}]
        tokens = estimate_messages_tokens(messages)
        assert tokens >= 0

    def test_long_message_scales(self):
        short = [{"role": "user", "content": "hi"}]
        long = [{"role": "user", "content": "x" * 10000}]
        assert estimate_messages_tokens(long) > estimate_messages_tokens(short) * 10


class TestCompactContext:
    def test_no_compaction_needed(self):
        """When under both thresholds, return messages unchanged."""
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
        """When compaction is disabled, prune old messages."""
        messages = [{"role": "system", "content": "prompt"}]
        for i in range(25):
            messages.append({"role": "user", "content": f"msg {i}"})

        config = MagicMock()
        config.get.side_effect = lambda k, d=None: {
            "max_context_messages": 5,
            "max_context_tokens": 1,  # Force compaction
            "compaction_enabled": False,
        }.get(k, d)

        result = compact_context(messages, config)
        # Should keep system prompt + last 5 messages
        assert result[0]["role"] == "system"
        assert len(result) == 6  # 1 system + 5 kept

    @patch("core.context.call_active_llm")
    def test_compaction_with_summary(self, mock_llm):
        """When compaction triggers, summarize old messages."""
        mock_llm.return_value = "Summary of conversation about Python testing."
        
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
        # Should have: system prompt + summary + recent messages
        assert len(result) >= 3
        assert result[0]["role"] == "system"
        # Summary message should be present
        summary_msgs = [m for m in result if "Summary of previous conversation" in m.get("content", "")]
        assert len(summary_msgs) == 1

    @patch("core.context.call_active_llm")
    def test_compaction_fallback_on_failure(self, mock_llm):
        """When summarization fails, fall back to pruning."""
        mock_llm.return_value = ""  # Empty = failure
        
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
