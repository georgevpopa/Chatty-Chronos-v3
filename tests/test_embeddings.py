"""Tests for rag/embeddings.py — custom embedding functions for ChromaDB RAG."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── ChronosEmbeddingFunction ────────────────────────────────────────────────
class TestChronosEmbeddingFunction:
    def test_name_returns_chronos_default(self):
        from rag.embeddings import ChronosEmbeddingFunction
        from core.config import Config
        config = Config()
        ef = ChronosEmbeddingFunction(config)
        assert ef.name() == "chronos_default"

    def test_embed_documents_delegates_to_call(self):
        from rag.embeddings import ChronosEmbeddingFunction
        from core.config import Config
        config = Config()
        ef = ChronosEmbeddingFunction(config)

        with patch.object(ef, "__call__", return_value=[[0.1, 0.2], [0.3, 0.4]]):
            result = ef.embed_documents(["hello", "world"])
            assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_embed_query_delegates_to_call(self):
        from rag.embeddings import ChronosEmbeddingFunction
        from core.config import Config
        config = Config()
        ef = ChronosEmbeddingFunction(config)

        with patch.object(ef, "__call__", return_value=[[0.5, 0.6]]):
            result = ef.embed_query(["query"])
            assert result == [[0.5, 0.6]]


# ─── Ollama provider ─────────────────────────────────────────────────────────
class TestOllamaEmbeddings:
    def test_ollama_batch_embeddings(self):
        """Ollama provider uses client.embed for batch embeddings."""
        mock_ollama = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2], [0.3, 0.4]]
        mock_client.embed.return_value = mock_response
        mock_ollama.Client.return_value = mock_client

        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            from rag.embeddings import ChronosEmbeddingFunction
            from core.config import Config
            config = Config()
            config.set("embedding_provider", "ollama")
            config.set("embedding_model", "nomic-embed-text")

            ef = ChronosEmbeddingFunction(config)
            result = ef(["hello", "world"])

            assert result == [[0.1, 0.2], [0.3, 0.4]]
            mock_client.embed.assert_called_once_with(model="nomic-embed-text", input=["hello", "world"])
        finally:
            if old:
                sys.modules["ollama"] = old
            else:
                sys.modules.pop("ollama", None)

    def test_ollama_fallback_to_single(self):
        """Ollama fallback to single-prompt embeddings when batch fails."""
        mock_ollama = MagicMock()
        mock_client = MagicMock()
        mock_client.embed.side_effect = Exception("batch not supported")
        mock_client.embeddings.return_value = {"embedding": [0.5]}
        mock_ollama.Client.return_value = mock_client

        old = sys.modules.get("ollama")
        sys.modules["ollama"] = mock_ollama

        try:
            from rag.embeddings import ChronosEmbeddingFunction
            from core.config import Config
            config = Config()
            config.set("embedding_provider", "ollama")
            config.set("embedding_model", "nomic-embed-text")

            ef = ChronosEmbeddingFunction(config)
            result = ef(["hello"])

            assert result == [[0.5]]
            mock_client.embeddings.assert_called_once_with(model="nomic-embed-text", prompt="hello")
        finally:
            if old:
                sys.modules["ollama"] = old
            else:
                sys.modules.pop("ollama", None)


# ─── llama.cpp provider ──────────────────────────────────────────────────────
class TestLlamaCppEmbeddings:
    @patch("rag.embeddings.httpx.Client")
    def test_llamacpp_embeddings(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from rag.embeddings import ChronosEmbeddingFunction
        from core.config import Config
        config = Config()
        config.set("embedding_provider", "llamacpp")
        config.set("llamacpp_host", "http://localhost:8080")
        config.set("embedding_model", "nomic-embed-text")

        ef = ChronosEmbeddingFunction(config)
        result = ef(["hello", "world"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        call_args = mock_client.post.call_args
        assert "8080" in call_args[0][0]
        assert call_args[1]["json"]["model"] == "nomic-embed-text"

    @patch("rag.embeddings.httpx.Client")
    def test_llamacpp_error_raises_runtime(self, mock_client_cls):
        mock_client_cls.side_effect = Exception("Connection refused")

        from rag.embeddings import ChronosEmbeddingFunction
        from core.config import Config
        config = Config()
        config.set("embedding_provider", "llamacpp")

        ef = ChronosEmbeddingFunction(config)

        with pytest.raises(RuntimeError, match="embedding error"):
            ef(["hello"])


# ─── Local provider ──────────────────────────────────────────────────────────
class TestLocalEmbeddings:
    def test_local_provider(self):
        """Local provider uses SentenceTransformerEmbeddingFunction."""
        mock_fn = MagicMock()
        mock_fn.return_value = [[0.1, 0.2], [0.3, 0.4]]

        mock_stf_module = MagicMock()
        mock_stf_module.SentenceTransformerEmbeddingFunction = MagicMock(return_value=mock_fn)

        old = sys.modules.get("chromadb.utils.embedding_functions")
        sys.modules["chromadb.utils.embedding_functions"] = mock_stf_module

        try:
            from rag.embeddings import ChronosEmbeddingFunction
            from core.config import Config
            config = Config()
            config.set("embedding_provider", "local")
            config.set("embedding_model", "all-MiniLM-L6-v2")

            ef = ChronosEmbeddingFunction(config)
            result = ef(["hello", "world"])

            assert result == [[0.1, 0.2], [0.3, 0.4]]
            mock_stf_module.SentenceTransformerEmbeddingFunction.assert_called_once_with(model_name="all-MiniLM-L6-v2")
        finally:
            if old:
                sys.modules["chromadb.utils.embedding_functions"] = old
            else:
                sys.modules.pop("chromadb.utils.embedding_functions", None)

    def test_local_provider_import_error(self):
        """Local provider raises ImportError when chromadb not available."""
        old = sys.modules.pop("chromadb.utils.embedding_functions", None)

        from rag.embeddings import ChronosEmbeddingFunction
        from core.config import Config
        config = Config()
        config.set("embedding_provider", "local")

        ef = ChronosEmbeddingFunction(config)

        sys.modules.pop("chromadb.utils.embedding_functions", None)
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            with pytest.raises(ImportError, match="chromadb is required"):
                ef(["hello"])

        if old:
            sys.modules["chromadb.utils.embedding_functions"] = old
