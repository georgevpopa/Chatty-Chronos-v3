"""Tests for llm/openai_provider.py — OpenAI-compatible cloud provider."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── chat ─────────────────────────────────────────────────────────────────────
class TestChat:
    @patch("llm.openai_provider.httpx.Client")
    def test_successful_call(self, mock_client_cls):
        """Successful chat returns LlamaCppResponse with content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from cloud!"}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.openai_provider import chat

        with patch.dict(os.environ, {"TEST_KEY": "sk-test-123"}):
            result = chat(
                messages=[{"role": "user", "content": "Hi"}],
                base_url="https://api.example.com/v1",
                api_key_name="TEST_KEY",
                model="gpt-4o"
            )

        assert result.message.content == "Hello from cloud!"
        assert result.message.tool_calls == []

    @patch("llm.openai_provider.httpx.Client")
    def test_with_tool_calls(self, mock_client_cls):
        """Response with tool_calls is parsed correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {
                "content": "",
                "tool_calls": [{"function": {"name": "read_file", "arguments": '{"path":"/tmp"}'}}]
            }}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.openai_provider import chat

        with patch.dict(os.environ, {"TEST_KEY": "sk-test"}):
            result = chat(
                messages=[{"role": "user", "content": "read file"}],
                base_url="https://api.example.com/v1",
                api_key_name="TEST_KEY",
                model="gpt-4o"
            )

        assert result.message.content == ""
        assert len(result.message.tool_calls) == 1

    def test_missing_api_key(self):
        """Raises ValueError when API key is not in environment."""
        from llm.openai_provider import chat

        with patch.dict(os.environ, {"HOME": "/tmp", "USERPROFILE": "/tmp"}, clear=False), \
             patch("dotenv.load_dotenv"):
            with pytest.raises(ValueError, match="API key not found"):
                chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    base_url="https://api.example.com/v1",
                    api_key_name="NONEXISTENT_KEY",
                    model="gpt-4o"
                )

    @patch("llm.openai_provider.httpx.Client")
    def test_message_formatting(self, mock_client_cls):
        """Messages are formatted correctly with tool_calls and tool_call_id."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "done"}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.openai_provider import chat

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "read_file", "arguments": "{}"}}
            ]},
            {"role": "tool", "content": "file contents", "tool_call_id": "call_123"},
            {"role": "user", "content": "thanks"},
        ]

        with patch.dict(os.environ, {"KEY": "sk-test"}):
            chat(messages, "https://api.example.com/v1", "KEY", "model")

        # Verify the payload
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert len(payload["messages"]) == 4
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][2]["tool_call_id"] == "call_123"

    @patch("llm.openai_provider.httpx.Client")
    def test_tools_included_when_provided(self, mock_client_cls):
        """Tools are included in payload when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.openai_provider import chat

        tools = [{"type": "function", "function": {"name": "test"}}]

        with patch.dict(os.environ, {"KEY": "sk-test"}):
            chat([{"role": "user", "content": "hi"}], "https://api.example.com/v1", "KEY", "model", tools=tools)

        payload = mock_client.post.call_args[1]["json"]
        assert "tools" in payload
        assert payload["tools"] == tools

    @patch("llm.openai_provider.httpx.Client")
    def test_no_tools_when_none(self, mock_client_cls):
        """No tools key in payload when tools is None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.openai_provider import chat

        with patch.dict(os.environ, {"KEY": "sk-test"}):
            chat([{"role": "user", "content": "hi"}], "https://api.example.com/v1", "KEY", "model", tools=None)

        payload = mock_client.post.call_args[1]["json"]
        assert "tools" not in payload

    @patch("llm.openai_provider.httpx.Client")
    def test_correct_url_construction(self, mock_client_cls):
        """URL is constructed as base_url + /chat/completions."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.openai_provider import chat

        with patch.dict(os.environ, {"KEY": "sk-test"}):
            chat([{"role": "user", "content": "hi"}], "https://api.groq.com/openai/v1", "KEY", "model")

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://api.groq.com/openai/v1/chat/completions"

    @patch("llm.openai_provider.httpx.Client")
    def test_authorization_header(self, mock_client_cls):
        """Authorization header includes Bearer token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.openai_provider import chat

        with patch.dict(os.environ, {"MY_KEY": "sk-secret-abc"}):
            chat([{"role": "user", "content": "hi"}], "https://api.example.com/v1", "MY_KEY", "model")

        call_args = mock_client.post.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer sk-secret-abc"

    @patch("llm.openai_provider.httpx.Client")
    def test_empty_content_response(self, mock_client_cls):
        """Response with null content returns empty string."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": None}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.openai_provider import chat

        with patch.dict(os.environ, {"KEY": "sk-test"}):
            result = chat([{"role": "user", "content": "hi"}], "https://api.example.com/v1", "KEY", "model")

        assert result.message.content == ""
