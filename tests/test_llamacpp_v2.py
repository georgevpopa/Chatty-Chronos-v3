"""Extended tests for llm/llamacpp_provider.py — bare JSON extraction, stream errors."""
import json
import pytest
from unittest.mock import patch, MagicMock


# ─── Bare JSON extraction from content ────────────────────────────────────────
class TestBareJsonExtraction:
    @patch("llm.llamacpp_provider.httpx.Client")
    def test_bare_json_extracted(self, mock_client_cls):
        """Model outputs raw JSON instead of using tool_calls format."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {
                "content": 'I will read the file.\n{"name": "read_file", "arguments": {"path": "/tmp/test.py"}}\nDone.',
                "tool_calls": None
            }}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        result = chat(
            [{"role": "user", "content": "read file"}],
            "http://localhost:8069",
            tools=[{"type": "function"}]
        )

        assert len(result.message.tool_calls) == 1
        assert result.message.tool_calls[0].function.name == "read_file"
        # Content should have the JSON stripped
        assert '"name"' not in result.message.content

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_bare_json_with_dict_arguments(self, mock_client_cls):
        """Bare JSON with dict arguments (not string)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {
                "content": '{"name": "grep", "arguments": {"pattern": "TODO", "path": "."}}',
                "tool_calls": None
            }}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        result = chat(
            [{"role": "user", "content": "search"}],
            "http://localhost:8069",
            tools=[{"type": "function"}]
        )

        assert len(result.message.tool_calls) == 1
        assert result.message.tool_calls[0].function.name == "grep"
        # Arguments come back as dict after LlamaCppMessage parses the JSON string
        assert isinstance(result.message.tool_calls[0].function.arguments, dict)

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_bare_json_invalid_skipped(self, mock_client_cls):
        """Invalid bare JSON is skipped gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {
                "content": 'Here is some code: {"name": "test", "arguments": {invalid json}}',
                "tool_calls": None
            }}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        result = chat(
            [{"role": "user", "content": "test"}],
            "http://localhost:8069",
            tools=[{"type": "function"}]
        )

        # Should not crash, tool_calls should be empty
        assert len(result.message.tool_calls) == 0

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_no_json_no_tools_returns_content(self, mock_client_cls):
        """Content without JSON and no tools returns as-is."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {
                "content": "Just plain text response.",
                "tool_calls": None
            }}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat
        result = chat(
            [{"role": "user", "content": "hello"}],
            "http://localhost:8069",
            tools=[{"type": "function"}]
        )

        assert result.message.content == "Just plain text response."
        assert len(result.message.tool_calls) == 0


# ─── Stream error paths ──────────────────────────────────────────────────────
class TestStreamErrors:
    @patch("llm.llamacpp_provider.httpx.Client")
    def test_stream_invalid_json_chunk(self, mock_client_cls):
        """Invalid JSON in stream is skipped."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = [
            'data: not valid json',
            'data: {"choices":[{"delta":{"content":"ok"}}]}',
            'data: [DONE]',
        ]
        mock_client = MagicMock()
        mock_client.stream.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat_stream
        chunks = list(chat_stream([{"role": "user", "content": "hi"}], "http://localhost:8069"))

        assert chunks == ["ok"]

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_stream_empty_content_chunk(self, mock_client_cls):
        """Empty content in stream chunk is skipped."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines.return_value = [
            'data: {"choices":[{"delta":{"content":""}}]}',
            'data: {"choices":[{"delta":{"content":"hello"}}]}',
            'data: [DONE]',
        ]
        mock_client = MagicMock()
        mock_client.stream.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.llamacpp_provider import chat_stream
        chunks = list(chat_stream([{"role": "user", "content": "hi"}], "http://localhost:8069"))

        assert chunks == ["hello"]

    @patch("llm.llamacpp_provider.httpx.Client")
    def test_stream_timeout(self, mock_client_cls):
        mock_client_cls.side_effect = Exception("Timeout")

        from llm.llamacpp_provider import chat_stream
        with pytest.raises(Exception):
            list(chat_stream([{"role": "user", "content": "hi"}], "http://localhost:8069", timeout=1))
