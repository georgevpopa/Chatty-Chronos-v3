"""Tests for the WebSearch tool (tools/web.py) — parsing without live network."""
from unittest.mock import patch, MagicMock
import io


MOCK_DDG_HTML = """
<html><body>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpython">Python.org</a>
  <a class="result__snippet">The official home of the Python programming language.</a>
</div>
<div class="result">
  <a class="result__a" href="https://docs.example.com/guide">Docs Guide</a>
  <a class="result__snippet">A helpful <b>guide</b> to everything.</a>
</div>
</body></html>
"""


def _mock_urlopen(*args, **kwargs):
    cm = MagicMock()
    cm.read.return_value = MOCK_DDG_HTML.encode("utf-8")
    cm.__enter__ = lambda s: cm
    cm.__exit__ = lambda s, *a: False
    return cm


class TestWebSearch:
    def test_registered_in_registry(self):
        from tools.registry import get_all_tools
        names = [t.name for t in get_all_tools()]
        assert "web_search" in names

    def test_schema_and_permission(self):
        from tools.web import WebSearch
        ws = WebSearch()
        assert ws.name == "web_search"
        assert ws.requires_permission is False
        schema = ws.to_ollama_schema()
        assert schema["function"]["name"] == "web_search"
        assert "query" in schema["function"]["parameters"]["properties"]

    def test_parses_results(self):
        from tools.web import WebSearch
        with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
            out = WebSearch().execute(query="python", max_results=5)
        assert "Python.org" in out
        assert "official home of the Python" in out
        # DuckDuckGo redirect link resolved to the real URL
        assert "https://example.com/python" in out
        # Tags stripped from snippet
        assert "<b>" not in out
        assert "Docs Guide" in out

    def test_max_results_capping(self):
        from tools.web import WebSearch
        with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
            out = WebSearch().execute(query="python", max_results=1)
        assert "Python.org" in out
        assert "Docs Guide" not in out  # capped to 1 result

    def test_network_error_is_graceful(self):
        from tools.web import WebSearch
        with patch("urllib.request.urlopen", side_effect=Exception("no network")):
            out = WebSearch().execute(query="python")
        assert "failed" in out.lower()

    def test_no_results_message(self):
        from tools.web import WebSearch
        empty = MagicMock()
        empty.read.return_value = b"<html><body>nothing here</body></html>"
        empty.__enter__ = lambda s: empty
        empty.__exit__ = lambda s, *a: False
        with patch("urllib.request.urlopen", return_value=empty):
            out = WebSearch().execute(query="zxcvqwerty")
        assert "No web results" in out
