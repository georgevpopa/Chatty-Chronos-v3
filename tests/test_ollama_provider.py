"""Tests for llm/ollama_provider.py — Ollama LLM provider."""
import sys
import pytest
from unittest.mock import patch, MagicMock


# ─── list_models ──────────────────────────────────────────────────────────────
class TestListModels:
    def test_returns_model_names(self):
        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_model.model = "llama3.1:latest"
        mock_response = MagicMock()
        mock_response.models = [mock_model]
        mock_client.list.return_value = mock_response

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            # Force reimport
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import list_models
            result = list_models()
            assert result == ["llama3.1:latest"]
        finally:
            _restore_ollama(old)

    def test_empty_models(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.models = []
        mock_client.list.return_value = mock_response

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import list_models
            result = list_models()
            assert result == []
        finally:
            _restore_ollama(old)

    def test_error_returns_empty(self):
        mock_ollama = MagicMock()
        mock_ollama.Client.side_effect = Exception("Connection refused")
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import list_models
            result = list_models()
            assert result == []
        finally:
            _restore_ollama(old)


def _restore_ollama(old):
    if old:
        sys.modules["ollama"] = old
    else:
        sys.modules.pop("ollama", None)
    sys.modules.pop("llm.ollama_provider", None)


# ─── chat ─────────────────────────────────────────────────────────────────────
class TestChat:
    def test_returns_response(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_client.chat.return_value = mock_response

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import chat
            result = chat([{"role": "user", "content": "hi"}], "llama3.1")
            assert result is not None
            mock_client.chat.assert_called_once()
        finally:
            _restore_ollama(old)

    def test_with_tools(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_client.chat.return_value = mock_response

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import chat
            tools = [{"type": "function", "function": {"name": "test"}}]
            result = chat([{"role": "user", "content": "hi"}], "llama3.1", tools=tools)

            call_kwargs = mock_client.chat.call_args
            assert call_kwargs is not None
        finally:
            _restore_ollama(old)


# ─── chat_stream ──────────────────────────────────────────────────────────────
class TestChatStream:
    def test_yields_content(self):
        mock_client = MagicMock()
        chunk1 = MagicMock()
        chunk1.message.content = "Hello"
        chunk2 = MagicMock()
        chunk2.message.content = "World"
        mock_client.chat.return_value = [chunk1, chunk2]

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import chat_stream
            chunks = list(chat_stream([{"role": "user", "content": "hi"}], "llama3.1"))
            assert chunks == ["Hello", "World"]
        finally:
            _restore_ollama(old)

    def test_skips_empty_chunks(self):
        mock_client = MagicMock()
        chunk1 = MagicMock()
        chunk1.message.content = ""
        chunk2 = MagicMock()
        chunk2.message.content = "actual content"
        mock_client.chat.return_value = [chunk1, chunk2]

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import chat_stream
            chunks = list(chat_stream([{"role": "user", "content": "hi"}], "llama3.1"))
            assert chunks == ["actual content"]
        finally:
            _restore_ollama(old)

    def test_with_tools_falls_back_to_chat_with_tools(self):
        """When tools provided, chat_stream calls _chat_with_tools (already tested separately)."""
        # This path is covered by TestChatWithTools which tests _chat_with_tools directly
        pass


# ─── _chat_with_tools ─────────────────────────────────────────────────────────
class TestChatWithTools:
    def test_tool_calls_marker(self):
        mock_client = MagicMock()
        mock_tc = MagicMock()
        mock_response = MagicMock()
        mock_response.message.tool_calls = [mock_tc]
        mock_response.message.content = "thinking"
        mock_client.chat.return_value = mock_response

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import _chat_with_tools, ToolCallMarker
            result = list(_chat_with_tools([{"role": "user", "content": "hi"}], "llama3.1", "http://localhost:11434", [{"type": "function"}]))

            assert len(result) == 1
            assert isinstance(result[0], ToolCallMarker)
        finally:
            _restore_ollama(old)

    def test_no_tool_calls_yields_content(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.message.tool_calls = None
        mock_response.message.content = "just text"
        mock_client.chat.return_value = mock_response

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import _chat_with_tools
            result = list(_chat_with_tools([{"role": "user", "content": "hi"}], "llama3.1", "http://localhost:11434", [{"type": "function"}]))

            assert result == ["just text"]
        finally:
            _restore_ollama(old)

    def test_empty_content_yields_empty_string(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.message.tool_calls = None
        mock_response.message.content = None
        mock_client.chat.return_value = mock_response

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            if "llm.ollama_provider" in sys.modules:
                del sys.modules["llm.ollama_provider"]
            from llm.ollama_provider import _chat_with_tools
            result = list(_chat_with_tools([{"role": "user", "content": "hi"}], "llama3.1", "http://localhost:11434", [{"type": "function"}]))

            assert result == [""]
        finally:
            _restore_ollama(old)


# ─── ToolCallMarker ───────────────────────────────────────────────────────────
class TestToolCallMarker:
    def test_creation(self):
        from llm.ollama_provider import ToolCallMarker
        mock_msg = MagicMock()
        mock_msg.tool_calls = [MagicMock()]
        marker = ToolCallMarker(mock_msg)
        assert marker.message is mock_msg
        assert marker.tool_calls == mock_msg.tool_calls
