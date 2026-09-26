"""Tests for LLM providers — formatting and response handling."""
import json
import pytest
from unittest.mock import patch, MagicMock
from llm.llamacpp_provider import LlamaCppResponse, LlamaCppMessage, LlamaCppToolCall, chat


class TestLlamaCppResponse:
    def test_basic_response(self):
        resp = LlamaCppResponse("Hello world")
        assert resp.message.content == "Hello world"
        assert resp.message.tool_calls == []

    def test_response_with_tool_calls(self):
        tool_calls = [{"function": {"name": "read_file", "arguments": '{"path": "/tmp/test.py"}'}}]
        resp = LlamaCppResponse("Let me read that", tool_calls)
        assert resp.message.content == "Let me read that"
        assert len(resp.message.tool_calls) == 1
        assert resp.message.tool_calls[0].function.name == "read_file"

    def test_empty_content(self):
        resp = LlamaCppResponse("")
        assert resp.message.content == ""

    def test_none_content(self):
        resp = LlamaCppResponse(None)
        # LlamaCppMessage stores content as-is (None stays None)
        assert resp.message.content is None


class TestLlamaCppMessage:
    def test_tool_call_parsing_json_string(self):
        """Arguments as JSON string should be parsed."""
        msg = LlamaCppMessage(
            content="test",
            tool_calls=[{"function": {"name": "grep", "arguments": '{"pattern": "TODO", "path": "."}'}}]
        )
        assert msg.tool_calls[0].function.arguments == {"pattern": "TODO", "path": "."}

    def test_tool_call_parsing_dict(self):
        """Arguments as dict should be kept as-is."""
        msg = LlamaCppMessage(
            content="test",
            tool_calls=[{"function": {"name": "grep", "arguments": {"pattern": "TODO", "path": "."}}}]
        )
        assert msg.tool_calls[0].function.arguments == {"pattern": "TODO", "path": "."}

    def test_no_tool_calls(self):
        msg = LlamaCppMessage(content="hello")
        assert msg.tool_calls == []


class TestChatFormatting:
    @patch("llm.llamacpp_provider.httpx.Client")
    def test_chat_formats_messages_correctly(self, mock_client_cls):
        """Verify messages are formatted correctly for the API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response", "tool_calls": None}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "read_file", "arguments": {"path": "/tmp/test.py"}}}
            ]},
            {"role": "tool", "content": "file contents here"},
        ]

        resp = chat(messages, "http://localhost:8069", "local")

        # Verify the POST was called
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]

        assert payload["model"] == "local"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][2]["role"] == "assistant"
        assert "tool_calls" in payload["messages"][2]
        assert payload["messages"][3]["role"] == "tool"
        assert payload["messages"][3]["content"] == "file contents here"

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_chat_includes_tools_when_provided(self, mock_client_cls):
        """When tools are passed, they appear in payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        tools = [{"type": "function", "function": {"name": "test", "parameters": {}}}]
        messages = [{"role": "user", "content": "hello"}]

        chat(messages, "http://localhost:8069", "local", tools=tools)

        payload = mock_client.post.call_args[1]["json"]
        assert "tools" in payload
        assert len(payload["tools"]) == 1

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_chat_no_tools_when_none(self, mock_client_cls):
        """When tools is None, payload has no tools key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        messages = [{"role": "user", "content": "hello"}]
        chat(messages, "http://localhost:8069", "local", tools=None)

        payload = mock_client.post.call_args[1]["json"]
        assert "tools" not in payload
