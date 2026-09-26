"""Tests for llm/llamacpp_provider.py — llama.cpp server provider."""
import json
import uuid
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── Helper classes ───────────────────────────────────────────────────────────
class TestLlamaCppFunction:
    def test_creation(self):
        from llm.llamacpp_provider import LlamaCppFunction
        fn = LlamaCppFunction("read_file", {"path": "/tmp"})
        assert fn.name == "read_file"
        assert fn.arguments == {"path": "/tmp"}


class TestLlamaCppToolCall:
    def test_creation(self):
        from llm.llamacpp_provider import LlamaCppToolCall
        tc = LlamaCppToolCall("read_file", {"path": "/tmp"})
        assert tc.function.name == "read_file"
        assert tc.function.arguments == {"path": "/tmp"}


class TestLlamaCppMessage:
    def test_basic_content(self):
        from llm.llamacpp_provider import LlamaCppMessage
        msg = LlamaCppMessage("hello")
        assert msg.content == "hello"
        assert msg.tool_calls == []

    def test_with_tool_calls(self):
        from llm.llamacpp_provider import LlamaCppMessage
        tool_calls = [{"function": {"name": "read_file", "arguments": '{"path": "/tmp"}'}}]
        msg = LlamaCppMessage("thinking", tool_calls)
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].function.name == "read_file"

    def test_tool_call_json_string_parsed(self):
        from llm.llamacpp_provider import LlamaCppMessage
        tool_calls = [{"function": {"name": "grep", "arguments": '{"pattern": "TODO", "path": "."}'}}]
        msg = LlamaCppMessage("searching", tool_calls)
        assert msg.tool_calls[0].function.arguments == {"pattern": "TODO", "path": "."}

    def test_tool_call_dict_arguments(self):
        from llm.llamacpp_provider import LlamaCppMessage
        tool_calls = [{"function": {"name": "grep", "arguments": {"pattern": "TODO"}}}]
        msg = LlamaCppMessage("searching", tool_calls)
        assert msg.tool_calls[0].function.arguments == {"pattern": "TODO"}

    def test_no_tool_calls(self):
        from llm.llamacpp_provider import LlamaCppMessage
        msg = LlamaCppMessage("hello", None)
        assert msg.tool_calls == []

    def test_empty_tool_calls(self):
        from llm.llamacpp_provider import LlamaCppMessage
        msg = LlamaCppMessage("hello", [])
        assert msg.tool_calls == []


class TestLlamaCppResponse:
    def test_basic(self):
        from llm.llamacpp_provider import LlamaCppResponse
        resp = LlamaCppResponse("hello")
        assert resp.message.content == "hello"
        assert resp.message.tool_calls == []


# ─── chat function ────────────────────────────────────────────────────────────
class TestChat:
    @patch("llm.llamacpp_provider.httpx.Client")
    def test_simple_response(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!", "tool_calls": None}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        result = chat([{"role": "user", "content": "hi"}], "http://localhost:8069")

        assert result.message.content == "Hello!"

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_with_tools(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "", "tool_calls": [{"function": {"name": "read_file", "arguments": "{}"}}]}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        tools = [{"type": "function", "function": {"name": "read_file"}}]
        result = chat([{"role": "user", "content": "hi"}], "http://localhost:8069", tools=tools)

        assert len(result.message.tool_calls) == 1
        payload = mock_client.post.call_args[1]["json"]
        assert "tools" in payload

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_no_tools_in_payload(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        result = chat([{"role": "user", "content": "hi"}], "http://localhost:8069", tools=None)

        payload = mock_client.post.call_args[1]["json"]
        assert "tools" not in payload

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_message_formatting(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "read_file", "arguments": "{}"}}]},
            {"role": "tool", "content": "file contents", "tool_call_id": "call_123"},
            {"role": "user", "content": "thanks"},
        ]

        chat(messages, "http://localhost:8069")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][2]["tool_call_id"] == "call_123"

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_timeout_error(self, mock_client_cls):
        mock_client_cls.side_effect = Exception("Timeout")

        from llm.llamacpp_provider import chat
        with pytest.raises(Exception):
            chat([{"role": "user", "content": "hi"}], "http://localhost:8069", timeout=1)

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_http_error_logged(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = Exception("500")
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        with pytest.raises(Exception):
            chat([{"role": "user", "content": "hi"}], "http://localhost:8069")

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_json_extraction_from_content(self, mock_client_cls):
        """When model outputs JSON in content instead of tool_calls, it's extracted."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {
                "content": 'I will read the file.\n```json\n{"name": "read_file", "arguments": {"path": "/tmp/test.py"}}\n```',
                "tool_calls": None
            }}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        result = chat([{"role": "user", "content": "read file"}], "http://localhost:8069", tools=[{"type": "function"}])

        assert len(result.message.tool_calls) == 1
        assert result.message.tool_calls[0].function.name == "read_file"

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_empty_content(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": None}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        result = chat([{"role": "user", "content": "hi"}], "http://localhost:8069")

        assert result.message.content == ""


# ─── chat_stream ──────────────────────────────────────────────────────────────
class TestChatStream:
    @patch("llm.llamacpp_provider.httpx.Client")
    def test_stream_yields_content(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" World"}}]}',
            'data: [DONE]',
        ]
        mock_client = MagicMock()
        mock_client.stream.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat_stream
        chunks = list(chat_stream([{"role": "user", "content": "hi"}], "http://localhost:8069"))

        assert chunks == ["Hello", " World"]

    @patch("llm.llamacpp_provider.chat")
    def test_stream_with_tools_falls_back(self, mock_chat):
        from llm.llamacpp_provider import LlamaCppResponse
        mock_chat.return_value = LlamaCppResponse("response", [{"function": {"name": "read_file", "arguments": "{}"}}])

        from llm.llamacpp_provider import chat_stream
        from llm.ollama_provider import ToolCallMarker
        chunks = list(chat_stream([{"role": "user", "content": "hi"}], "http://localhost:8069", tools=[{"type": "function"}]))

        assert len(chunks) == 1
        assert isinstance(chunks[0], ToolCallMarker)

    @patch("llm.llamacpp_provider.chat")
    def test_stream_with_tools_no_calls(self, mock_chat):
        from llm.llamacpp_provider import LlamaCppResponse
        mock_chat.return_value = LlamaCppResponse("response text")

        from llm.llamacpp_provider import chat_stream
        chunks = list(chat_stream([{"role": "user", "content": "hi"}], "http://localhost:8069", tools=[{"type": "function"}]))

        assert chunks == ["response text"]


# ─── is_available ─────────────────────────────────────────────────────────────
class TestIsAvailable:
    @patch("llm.llamacpp_provider.httpx.Client")
    def test_server_up(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import is_available
        assert is_available("http://localhost:8069") is True

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_server_down(self, mock_client_cls):
        mock_client_cls.side_effect = Exception("Connection refused")

        from llm.llamacpp_provider import is_available
        assert is_available("http://localhost:8069") is False

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_server_500(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import is_available
        assert is_available("http://localhost:8069") is False
