"""Tests for core/memory.py — persistent memory store and search."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── init_memory ──────────────────────────────────────────────────────────────
class TestInitMemory:
    def test_init_with_chromadb(self, tmp_path):
        """Init creates ChromaDB client when chromadb is available."""
        import sys
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

        try:
            import core.memory as mem
            mem._memory_client = None
            mem._collection = None
            result = mem.init_memory()

            assert result is True
            assert mem._collection is not None
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
            import core.memory as mem
            mem._memory_client = None
            mem._collection = None

    def test_init_without_chromadb(self, tmp_path):
        """Init falls back to JSON file when chromadb is not available."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        try:
            import core.memory as mem
            mem.chromadb = None
            mem._memory_client = None
            mem._collection = None
            mem._fallback_facts = []

            result = mem.init_memory()
            assert result is True
            assert mem._collection is None
        finally:
            if old_chroma:
                sys.modules["chromadb"] = old_chroma
            import core.memory as mem
            mem._collection = None

    def test_init_loads_existing_fallback(self, tmp_path):
        """Init loads existing fallback JSON file."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        fallback_file = tmp_path / "memory.json"
        fallback_file.write_text(json.dumps([{"key": "k1", "content": "v1"}]))

        try:
            import core.memory as mem
            mem.chromadb = None
            mem._memory_client = None
            mem._collection = None
            mem._fallback_memory_file = fallback_file
            mem._fallback_facts = []

            result = mem.init_memory()
            assert result is True
            assert len(mem._fallback_facts) == 1
            assert mem._fallback_facts[0]["key"] == "k1"
        finally:
            if old_chroma:
                sys.modules["chromadb"] = old_chroma
            import core.memory as mem
            mem._collection = None


# ─── store_memory ─────────────────────────────────────────────────────────────
class TestStoreMemory:
    def test_store_with_collection(self):
        """Store to ChromaDB when collection is available."""
        import sys
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

        try:
            import core.memory as mem
            mem._collection = mock_collection
            result = mem.store_memory("test_key", "test content", {"source": "test"})

            assert result is True
            mock_collection.add.assert_called_once()
            call_kwargs = mock_collection.add.call_args[1]
            assert call_kwargs["documents"] == ["test content"]
            assert call_kwargs["ids"] == ["test_key"]
        finally:
            import core.memory as mem
            mem._collection = None

    def test_store_without_collection(self, tmp_path):
        """Store to JSON fallback when no collection."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        fallback_file = tmp_path / "memory.json"

        try:
            import core.memory as mem
            mem.chromadb = None
            mem._collection = None
            mem._fallback_memory_file = fallback_file
            mem._fallback_facts = []

            result = mem.store_memory("key1", "content1", {"tag": "test"})

            assert result is True
            assert len(mem._fallback_facts) == 1
            assert mem._fallback_facts[0]["key"] == "key1"
            assert fallback_file.exists()

            with open(fallback_file) as f:
                data = json.load(f)
            assert data[0]["content"] == "content1"
        finally:
            if "chromadb" in sys.modules:
                del sys.modules["chromadb"]
            import core.memory as mem
            mem._collection = None

    def test_store_appends_to_existing(self, tmp_path):
        """Multiple stores append to fallback list."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        fallback_file = tmp_path / "memory.json"

        try:
            import core.memory as mem
            mem.chromadb = None
            mem._collection = None
            mem._fallback_memory_file = fallback_file
            mem._fallback_facts = []

            mem.store_memory("k1", "v1")
            mem.store_memory("k2", "v2")

            assert len(mem._fallback_facts) == 2
            assert mem._fallback_facts[0]["key"] == "k1"
            assert mem._fallback_facts[1]["key"] == "k2"
        finally:
            if "chromadb" in sys.modules:
                del sys.modules["chromadb"]
            import core.memory as mem
            mem._collection = None


# ─── search_memory ────────────────────────────────────────────────────────────
class TestSearchMemory:
    def test_search_with_collection(self):
        """Search using ChromaDB collection."""
        import sys
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_collection.query.return_value = {
            "documents": [["found content"]],
            "metadatas": [[{"key": "k1"}]],
        }

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            import core.memory as mem
            mem._collection = mock_collection
            results = mem.search_memory("test query")

            assert len(results) == 1
            assert results[0]["content"] == "found content"
            assert results[0]["metadata"]["key"] == "k1"
        finally:
            import core.memory as mem
            mem._collection = None

    def test_search_empty_collection(self):
        """Search returns empty when collection returns nothing."""
        import sys
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_collection.query.return_value = {"documents": [[]], "metadatas": [[]]}

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            import core.memory as mem
            mem._collection = mock_collection
            results = mem.search_memory("nothing here")
            assert results == []
        finally:
            import core.memory as mem
            mem._collection = None

    def test_search_fallback_keyword_match(self, tmp_path):
        """Fallback search matches keywords in content."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        try:
            import core.memory as mem
            mem.chromadb = None
            mem._collection = None
            mem._fallback_facts = [
                {"key": "k1", "content": "I love Python programming"},
                {"key": "k2", "content": "JavaScript is fun"},
                {"key": "k3", "content": "Python testing with pytest"},
            ]

            results = mem.search_memory("Python")
            assert len(results) == 2
            assert all("Python" in r["content"] for r in results)
        finally:
            if "chromadb" in sys.modules:
                del sys.modules["chromadb"]
            import core.memory as mem
            mem._collection = None

    def test_search_fallback_n_results(self, tmp_path):
        """Fallback search respects n_results limit."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        try:
            import core.memory as mem
            mem.chromadb = None
            mem._collection = None
            mem._fallback_facts = [
                {"key": "k1", "content": "Python is great"},
                {"key": "k2", "content": "Python is awesome"},
                {"key": "k3", "content": "Python is cool"},
            ]

            results = mem.search_memory("Python", n_results=2)
            assert len(results) == 2
        finally:
            if "chromadb" in sys.modules:
                del sys.modules["chromadb"]
            import core.memory as mem
            mem._collection = None

    def test_search_fallback_no_match(self, tmp_path):
        """Fallback search returns empty when no match."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        try:
            import core.memory as mem
            mem.chromadb = None
            mem._collection = None
            mem._fallback_facts = [
                {"key": "k1", "content": "Python is great"},
            ]

            results = mem.search_memory("Rust")
            assert results == []
        finally:
            if "chromadb" in sys.modules:
                del sys.modules["chromadb"]
            import core.memory as mem
            mem._collection = None


# ─── Memory class ─────────────────────────────────────────────────────────────
class TestMemoryClass:
    def test_init_creates_memory(self):
        """Memory class initializes properly."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        try:
            from core.memory import Memory
            memory = Memory()
            assert memory.facts == []
        finally:
            if "chromadb" in sys.modules:
                del sys.modules["chromadb"]
            import core.memory as mem
            mem._collection = None

    def test_add_stores_fact(self, tmp_path):
        """Memory.add stores a fact."""
        import sys
        old_chroma = sys.modules.pop("chromadb", None)

        fallback_file = tmp_path / "memory.json"

        try:
            import core.memory as mem
            mem.chromadb = None
            mem._collection = None
            mem._fallback_memory_file = fallback_file
            mem._fallback_facts = []

            from core.memory import Memory
            memory = Memory()
            memory.add("I prefer dark theme")

            assert len(mem._fallback_facts) == 1
            assert mem._fallback_facts[0]["content"] == "I prefer dark theme"
        finally:
            if "chromadb" in sys.modules:
                del sys.modules["chromadb"]
            import core.memory as mem
            mem._collection = None

    def test_get_context_returns_empty(self):
        """Memory.get_context returns empty string (deprecated)."""
        from core.memory import Memory
        memory = Memory()
        assert memory.get_context() == ""
