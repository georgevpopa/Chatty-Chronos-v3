"""Tests for rag/retriever.py — query_knowledge and get_rag_context."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def _inject_mock_chromadb():
    """Inject a mock chromadb module into sys.modules for local imports."""
    mock_chroma = MagicMock()
    mock_settings = MagicMock()
    mock_chroma.config.Settings = mock_settings
    old = sys.modules.get("chromadb")
    sys.modules["chromadb"] = mock_chroma
    sys.modules["chromadb.config"] = mock_chroma.config
    return mock_chroma, old


def _restore_chromadb(old):
    """Restore original chromadb module."""
    if old:
        sys.modules["chromadb"] = old
    else:
        sys.modules.pop("chromadb", None)
    sys.modules.pop("chromadb.config", None)


def _make_config(tmp_path):
    """Create a Config that points at tmp_path so vectordb dir resolves correctly."""
    from core.config import Config
    with patch("core.config.Path.home", return_value=tmp_path):
        config = Config()
    # Config.dir = Path.home() / ".chatty-chronos", so create the vectordb inside it
    db_path = config.dir / "vectordb"
    db_path.mkdir(parents=True, exist_ok=True)
    return config


# ─── query_knowledge ───────────────────────────────────────────────────────────
class TestQueryKnowledge:
    def test_no_vectordb_returns_empty(self, tmp_path):
        """When vectordb directory doesn't exist, return empty."""
        mock_chroma, old = _inject_mock_chromadb()
        try:
            config = _make_config(tmp_path)
            # Remove vectordb so db_path.exists() returns False
            import shutil
            shutil.rmtree(config.dir / "vectordb", ignore_errors=True)

            from rag.retriever import query_knowledge
            results = query_knowledge("test question", config=config)
            assert results == []
        finally:
            _restore_chromadb(old)

    def test_empty_collection_returns_empty(self, tmp_path):
        """When collection is empty, return empty."""
        mock_chroma, old = _inject_mock_chromadb()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        try:
            config = _make_config(tmp_path)

            from rag.retriever import query_knowledge
            results = query_knowledge("test question", config=config)
            assert results == []
        finally:
            _restore_chromadb(old)

    def test_returns_formatted_results(self, tmp_path):
        """Query returns properly formatted results."""
        mock_chroma, old = _inject_mock_chromadb()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["def hello(): return 'world'"]],
            "metadatas": [[{"file": "app.py", "chunk_index": 0}]],
            "distances": [[0.3]],
        }
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        try:
            config = _make_config(tmp_path)

            from rag.retriever import query_knowledge
            results = query_knowledge("hello function", config=config)

            assert len(results) == 1
            assert results[0]["text"] == "def hello(): return 'world'"
            assert results[0]["file"] == "app.py"
            assert results[0]["chunk_index"] == 0
            assert results[0]["distance"] == 0.3
            assert "hybrid_score" in results[0]
        finally:
            _restore_chromadb(old)

    def test_keyword_reranking(self, tmp_path):
        """Results with more keyword matches score better."""
        mock_chroma, old = _inject_mock_chromadb()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [
                ["The function hello_world does X", "Completely unrelated text about cooking"],
            ],
            "metadatas": [
                [{"file": "a.py", "chunk_index": 0}, {"file": "b.py", "chunk_index": 0}],
            ],
            "distances": [[0.5, 0.5]],
        }
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        try:
            config = _make_config(tmp_path)

            from rag.retriever import query_knowledge
            results = query_knowledge("hello_world function", config=config)

            assert results[0]["file"] == "a.py"
            assert results[0]["hybrid_score"] < results[1]["hybrid_score"]
        finally:
            _restore_chromadb(old)

    def test_n_results_respected(self, tmp_path):
        """Only n_results results are returned."""
        mock_chroma, old = _inject_mock_chromadb()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["doc1", "doc2", "doc3", "doc4", "doc5"]],
            "metadatas": [
                [{"file": "a.py", "chunk_index": 0}, {"file": "b.py", "chunk_index": 0}, {"file": "c.py", "chunk_index": 0}, {"file": "d.py", "chunk_index": 0}, {"file": "e.py", "chunk_index": 0}],
            ],
            "distances": [[0.1, 0.2, 0.3, 0.4, 0.5]],
        }
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_collection.return_value = mock_collection

        try:
            config = _make_config(tmp_path)

            from rag.retriever import query_knowledge
            results = query_knowledge("test", n_results=2, config=config)

            assert len(results) == 2
        finally:
            _restore_chromadb(old)

    def test_collection_not_found_returns_empty(self, tmp_path):
        """When collection doesn't exist, return empty."""
        mock_chroma, old = _inject_mock_chromadb()
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_chroma.PersistentClient.return_value = mock_client

        try:
            config = _make_config(tmp_path)

            from rag.retriever import query_knowledge
            results = query_knowledge("test", config=config)
            assert results == []
        finally:
            _restore_chromadb(old)


# ─── get_rag_context ───────────────────────────────────────────────────────────
class TestGetRagContext:
    @patch("rag.retriever.query_knowledge")
    def test_empty_results_returns_empty(self, mock_query):
        mock_query.return_value = []

        from rag.retriever import get_rag_context
        context = get_rag_context("test")
        assert context == ""

    @patch("rag.retriever.query_knowledge")
    def test_formats_context_correctly(self, mock_query):
        mock_query.return_value = [
            {"text": "def hello(): pass", "file": "app.py", "chunk_index": 0,
             "distance": 0.3, "hybrid_score": 0.2},
        ]

        from rag.retriever import get_rag_context
        context = get_rag_context("hello function")

        assert "## Relevant context from indexed knowledge:" in context
        assert "[app.py]" in context
        assert "def hello(): pass" in context

    @patch("rag.retriever.query_knowledge")
    def test_multiple_results(self, mock_query):
        mock_query.return_value = [
            {"text": "code1", "file": "a.py", "chunk_index": 0,
             "distance": 0.1, "hybrid_score": 0.1},
            {"text": "code2", "file": "b.py", "chunk_index": 0,
             "distance": 0.2, "hybrid_score": 0.2},
        ]

        from rag.retriever import get_rag_context
        context = get_rag_context("test")

        assert "[a.py]" in context
        assert "[b.py]" in context
        assert "code1" in context
        assert "code2" in context

    @patch("rag.retriever.query_knowledge")
    def test_separators_between_chunks(self, mock_query):
        mock_query.return_value = [
            {"text": "chunk1", "file": "a.py", "chunk_index": 0,
             "distance": 0.1, "hybrid_score": 0.1},
            {"text": "chunk2", "file": "b.py", "chunk_index": 0,
             "distance": 0.2, "hybrid_score": 0.2},
        ]

        from rag.retriever import get_rag_context
        context = get_rag_context("test")

        assert "---" in context
