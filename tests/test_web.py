"""Tests for tools/web.py — web browsing and scraping tools."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── SimpleHTMLToTextParser ───────────────────────────────────────────────────
class TestHTMLParser:
    def test_basic_text_extraction(self):
        from tools.web import SimpleHTMLToTextParser
        parser = SimpleHTMLToTextParser()
        parser.feed("<html><body><p>Hello World</p></body></html>")
        parser.close()
        text = "".join(parser.text)
        assert "Hello World" in text

    def test_script_ignored(self):
        from tools.web import SimpleHTMLToTextParser
        parser = SimpleHTMLToTextParser()
        parser.feed("<html><head><script>alert('hi')</script></head><body><p>visible</p></body></html>")
        parser.close()
        text = "".join(parser.text)
        assert "alert" not in text
        assert "visible" in text

    def test_style_ignored(self):
        from tools.web import SimpleHTMLToTextParser
        parser = SimpleHTMLToTextParser()
        parser.feed("<html><head><style>body { color: red; }</style></head><body><p>text</p></body></html>")
        parser.close()
        text = "".join(parser.text)
        assert "color" not in text
        assert "text" in text

    def test_nested_tags(self):
        from tools.web import SimpleHTMLToTextParser
        parser = SimpleHTMLToTextParser()
        parser.feed("<div><p>Line 1</p><p>Line 2</p></div>")
        parser.close()
        text = "".join(parser.text)
        assert "Line 1" in text
        assert "Line 2" in text

    def test_newlines_for_block_elements(self):
        from tools.web import SimpleHTMLToTextParser
        parser = SimpleHTMLToTextParser()
        parser.feed("<h1>Title</h1><p>Paragraph</p><li>Item</li>")
        parser.close()
        text = "".join(parser.text)
        assert "Title" in text
        assert "Paragraph" in text
        assert "Item" in text

    def test_noscript_ignored(self):
        from tools.web import SimpleHTMLToTextParser
        parser = SimpleHTMLToTextParser()
        parser.feed("<body><p>visible</p><noscript>hidden</noscript></body>")
        parser.close()
        text = "".join(parser.text)
        assert "visible" in text
        assert "hidden" not in text

    def test_empty_html(self):
        from tools.web import SimpleHTMLToTextParser
        parser = SimpleHTMLToTextParser()
        parser.feed("")
        parser.close()
        text = "".join(parser.text)
        assert text.strip() == ""

    def test_malformed_html(self):
        from tools.web import SimpleHTMLToTextParser
        parser = SimpleHTMLToTextParser()
        parser.feed("<p>unclosed tag<div>nested</div>")
        parser.close()
        text = "".join(parser.text)
        assert "unclosed tag" in text or "nested" in text


# ─── _html_to_text ────────────────────────────────────────────────────────────
class TestHtmlToText:
    def test_converts_html_to_clean_text(self):
        from tools.web import _html_to_text
        html = "<html><body><h1>Title</h1><p>Content here</p></body></html>"
        result = _html_to_text(html)
        assert "Title" in result
        assert "Content here" in result
        assert "<" not in result  # No HTML tags in output

    def test_strips_excess_newlines(self):
        from tools.web import _html_to_text
        html = "<p>line1</p>\n\n\n<p>line2</p>"
        result = _html_to_text(html)
        lines = result.split("\n")
        # No consecutive empty lines
        assert "" not in lines

    def test_empty_html(self):
        from tools.web import _html_to_text
        result = _html_to_text("")
        assert result == ""

    def test_plain_text_passthrough(self):
        from tools.web import _html_to_text
        result = _html_to_text("Just plain text")
        assert "Just plain text" in result


# ─── FetchWebpage tool ───────────────────────────────────────────────────────
class TestFetchWebpage:
    def test_tool_creation(self):
        from tools.web import FetchWebpage
        tool = FetchWebpage()
        assert tool.name == "fetch_webpage"
        assert tool.requires_permission is False

    def test_tool_schema(self):
        from tools.web import FetchWebpage
        tool = FetchWebpage()
        schema = tool.to_ollama_schema()
        assert schema["function"]["name"] == "fetch_webpage"
        assert "url" in schema["function"]["parameters"]["properties"]

    def test_prepends_https(self):
        """URL without http prefix gets https:// prepended."""
        from tools.web import FetchWebpage
        import urllib.request

        mock_response = MagicMock()
        mock_response.headers.get_content_type.return_value = "text/html"
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.read.return_value = b"<p>Hello</p>"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        tool = FetchWebpage()
        with patch("tools.web.urllib.request.urlopen", return_value=mock_response):
            result = tool.execute("example.com")

        assert "Hello" in result

    @patch("tools.web.urllib.request.urlopen")
    def test_html_content_extracted(self, mock_urlopen):
        """HTML content is converted to text."""
        mock_response = MagicMock()
        mock_response.headers.get_content_type.return_value = "text/html"
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.read.return_value = b"<html><body><p>Hello World</p></body></html>"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        from tools.web import FetchWebpage
        tool = FetchWebpage()
        result = tool.execute("https://example.com")

        assert "Hello World" in result
        assert "<" not in result  # No HTML tags

    @patch("tools.web.urllib.request.urlopen")
    def test_json_content_passthrough(self, mock_urlopen):
        """Non-HTML content is passed through as-is."""
        mock_response = MagicMock()
        mock_response.headers.get_content_type.return_value = "application/json"
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.read.return_value = b'{"key": "value"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        from tools.web import FetchWebpage
        tool = FetchWebpage()
        result = tool.execute("https://api.example.com/data")

        assert '{"key": "value"}' in result

    @patch("tools.web.urllib.request.urlopen")
    def test_truncation(self, mock_urlopen):
        """Long content is truncated to 30000 chars."""
        mock_response = MagicMock()
        mock_response.headers.get_content_type.return_value = "text/plain"
        mock_response.headers.get_content_charset.return_value = "utf-8"
        mock_response.read.return_value = b"x" * 35000
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        from tools.web import FetchWebpage
        tool = FetchWebpage()
        result = tool.execute("https://example.com/big")

        assert len(result) < 35000
        assert "Truncated" in result

    @patch("tools.web.urllib.request.urlopen")
    def test_url_error(self, mock_urlopen):
        """URL errors are caught and returned as string."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Name not resolved")

        from tools.web import FetchWebpage
        tool = FetchWebpage()
        result = tool.execute("https://nonexistent.example.com")

        assert "Failed to fetch" in result

    @patch("tools.web.urllib.request.urlopen")
    def test_generic_exception(self, mock_urlopen):
        """Generic exceptions are caught."""
        mock_urlopen.side_effect = Exception("Something went wrong")

        from tools.web import FetchWebpage
        tool = FetchWebpage()
        result = tool.execute("https://example.com")

        assert "Error fetching" in result

    @patch("tools.web.urllib.request.urlopen")
    def test_unicode_decode_error(self, mock_urlopen):
        """Unicode decode errors are handled gracefully."""
        mock_response = MagicMock()
        mock_response.headers.get_content_type.return_value = "text/html"
        mock_response.headers.get_content_charset.return_value = "ascii"
        # Invalid ASCII bytes
        mock_response.read.return_value = b"<p>Hello</p>\xff\xfe"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        from tools.web import FetchWebpage
        tool = FetchWebpage()
        result = tool.execute("https://example.com")

        # Should not crash, content should be readable
        assert isinstance(result, str)
