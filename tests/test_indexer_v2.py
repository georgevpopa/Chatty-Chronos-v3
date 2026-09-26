"""Extended tests for rag/indexer.py — index_url full flow."""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── index_url ────────────────────────────────────────────────────────────────
class TestIndexUrl:
    def test_http_error_returns_zero(self):
        """Returns 0 when HTTP request fails."""
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Connection refused")
        old_req = sys.modules.get("requests")
        sys.modules["requests"] = mock_requests

        old_bs4 = sys.modules.get("bs4")
        sys.modules["bs4"] = MagicMock()

        try:
            from rag.indexer import index_url
            from core.config import Config
            config = Config()
            result = index_url("https://nonexistent.example.com", config=config)
            assert result == 0
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
            if old_req:
                sys.modules["requests"] = old_req
            else:
                sys.modules.pop("requests", None)
            if old_bs4:
                sys.modules["bs4"] = old_bs4
            else:
                sys.modules.pop("bs4", None)

    def test_empty_page_returns_zero(self):
        """Returns 0 when page has no useful text."""
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><head></head><body></body></html>"
        mock_requests.get.return_value = mock_response
        old_req = sys.modules.get("requests")
        sys.modules["requests"] = mock_requests

        from bs4 import BeautifulSoup
        old_bs4 = sys.modules.get("bs4")
        # bs4 is real, let it work

        try:
            from rag.indexer import index_url
            from core.config import Config
            config = Config()
            result = index_url("https://example.com/empty", config=config)
            assert result == 0
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
            if old_req:
                sys.modules["requests"] = old_req
            else:
                sys.modules.pop("requests", None)

    def test_successful_index(self):
        """Successfully indexes a web page."""
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><head><title>Test Page</title></head><body><p>Hello World content here.</p></body></html>"
        mock_requests.get.return_value = mock_response
        old_req = sys.modules.get("requests")
        sys.modules["requests"] = mock_requests

        old_bs4 = sys.modules.get("bs4")
        # bs4 is real, let it work

        try:
            from rag.indexer import index_url
            from core.config import Config
            config = Config()
            result = index_url("https://example.com/test", config=config)

            assert result >= 1
            mock_collection.upsert.assert_called()
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
            if old_req:
                sys.modules["requests"] = old_req
            else:
                sys.modules.pop("requests", None)

    def test_strips_scripts_and_styles(self):
        """HTML scripts and styles are stripped from content."""
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '<html><head><title>Page</title></head><body><script>alert("hidden")</script><style>.red{color:red}</style><p>Visible text</p></body></html>'
        mock_requests.get.return_value = mock_response
        old_req = sys.modules.get("requests")
        sys.modules["requests"] = mock_requests

        try:
            from rag.indexer import index_url
            from core.config import Config
            config = Config()
            result = index_url("https://example.com/test", config=config)

            assert result >= 1
            # Verify the indexed content doesn't contain script/style text
            call_args = mock_collection.upsert.call_args
            documents = call_args[1]["documents"]
            for doc in documents:
                assert "alert" not in doc
                assert "color:red" not in doc
                assert "Visible text" in doc
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
            if old_req:
                sys.modules["requests"] = old_req
            else:
                sys.modules.pop("requests", None)

    def test_page_title_used_in_metadata(self):
        """Page title is used in metadata."""
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><head><title>My Page Title</title></head><body><p>Content</p></body></html>"
        mock_requests.get.return_value = mock_response
        old_req = sys.modules.get("requests")
        sys.modules["requests"] = mock_requests

        try:
            from rag.indexer import index_url
            from core.config import Config
            config = Config()
            result = index_url("https://example.com/test", config=config)

            assert result >= 1
            call_args = mock_collection.upsert.call_args
            metadatas = call_args[1]["metadatas"]
            assert any(m.get("title") == "My Page Title" for m in metadatas)
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
            if old_req:
                sys.modules["requests"] = old_req
            else:
                sys.modules.pop("requests", None)

    def test_url_used_as_file_identifier(self):
        """URL is used as the file identifier in metadata."""
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Content</p></body></html>"
        mock_requests.get.return_value = mock_response
        old_req = sys.modules.get("requests")
        sys.modules["requests"] = mock_requests

        try:
            from rag.indexer import index_url
            from core.config import Config
            config = Config()
            url = "https://example.com/test-page"
            result = index_url(url, config=config)

            assert result >= 1
            call_args = mock_collection.upsert.call_args
            metadatas = call_args[1]["metadatas"]
            assert any(m.get("file") == url for m in metadatas)
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
            if old_req:
                sys.modules["requests"] = old_req
            else:
                sys.modules.pop("requests", None)
