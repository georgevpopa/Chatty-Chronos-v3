"""Tests for rag/indexer.py — chunking, gitignore, file collection, indexing."""
import os
import sys
import re
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ─── chunk_text ────────────────────────────────────────────────────────────────
class TestChunkText:
    def test_empty_text(self):
        from rag.indexer import chunk_text
        assert chunk_text("") == []

    def test_short_text_single_chunk(self):
        from rag.indexer import chunk_text
        chunks = chunk_text("hello world")
        assert len(chunks) == 1
        assert chunks[0] == "hello world"

    def test_exact_chunk_size(self):
        from rag.indexer import chunk_text
        text = "x" * 800
        chunks = chunk_text(text, chunk_size=800, overlap=100)
        assert len(chunks) >= 1
        assert chunks[0] == text[:800]

    def test_overlap_creates_continuity(self):
        from rag.indexer import chunk_text
        text = "a" * 1000
        chunks = chunk_text(text, chunk_size=500, overlap=100)
        assert len(chunks) >= 2
        assert chunks[1][:100] == text[400:500]

    def test_long_text_multiple_chunks(self):
        from rag.indexer import chunk_text
        text = "word " * 500
        chunks = chunk_text(text, chunk_size=800, overlap=100)
        assert len(chunks) > 3

    def test_preserves_content(self):
        from rag.indexer import chunk_text
        text = "A" * 300 + "B" * 300 + "C" * 300
        chunks = chunk_text(text, chunk_size=500, overlap=0)
        combined = "".join(chunks)
        assert "A" * 300 in combined
        assert "B" * 300 in combined
        assert "C" * 300 in combined


# ─── load_gitignore_patterns ──────────────────────────────────────────────────
class TestLoadGitignorePatterns:
    def test_no_gitignore(self, tmp_path):
        from rag.indexer import load_gitignore_patterns
        patterns = load_gitignore_patterns(tmp_path)
        assert patterns == []

    def test_empty_gitignore(self, tmp_path):
        (tmp_path / ".gitignore").write_text("")
        from rag.indexer import load_gitignore_patterns
        patterns = load_gitignore_patterns(tmp_path)
        assert patterns == []

    def test_comments_ignored(self, tmp_path):
        (tmp_path / ".gitignore").write_text("# this is a comment\n")
        from rag.indexer import load_gitignore_patterns
        patterns = load_gitignore_patterns(tmp_path)
        assert patterns == []

    def test_glob_pattern(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n")
        from rag.indexer import load_gitignore_patterns
        patterns = load_gitignore_patterns(tmp_path)
        assert len(patterns) == 1
        assert patterns[0].match("debug.log")
        assert not patterns[0].match("debug.txt")

    def test_directory_pattern(self, tmp_path):
        (tmp_path / ".gitignore").write_text("dist/\n")
        from rag.indexer import load_gitignore_patterns
        patterns = load_gitignore_patterns(tmp_path)
        assert len(patterns) == 1
        assert patterns[0].match("dist/") or patterns[0].match("dist/bundle.js")

    def test_multiple_patterns(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n*.tmp\nbuild/\n")
        from rag.indexer import load_gitignore_patterns
        patterns = load_gitignore_patterns(tmp_path)
        assert len(patterns) == 3


# ─── is_ignored ────────────────────────────────────────────────────────────────
class TestIsIgnored:
    def test_no_patterns(self, tmp_path):
        from rag.indexer import is_ignored
        assert is_ignored(tmp_path / "test.py", tmp_path, []) is False

    def test_matching_pattern(self, tmp_path):
        import re
        pattern = re.compile(r".*\.log$")
        from rag.indexer import is_ignored
        assert is_ignored(tmp_path / "debug.log", tmp_path, [pattern]) is True

    def test_non_matching_pattern(self, tmp_path):
        import re
        pattern = re.compile(r".*\.log$")
        from rag.indexer import is_ignored
        assert is_ignored(tmp_path / "test.py", tmp_path, [pattern]) is False

    def test_nested_path_matching(self, tmp_path):
        import re
        pattern = re.compile(r".*\.pyc$")
        from rag.indexer import is_ignored
        nested = tmp_path / "src" / "module"
        nested.mkdir(parents=True)
        assert is_ignored(nested / "cache.pyc", tmp_path, [pattern]) is True


# ─── collect_files ─────────────────────────────────────────────────────────────
class TestCollectFiles:
    def test_collect_txt_files(self, tmp_path):
        (tmp_path / "a.py").write_text("print('a')")
        (tmp_path / "b.txt").write_text("hello")
        (tmp_path / "c.exe").write_bytes(b"\x00\x00")

        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "a.py" in names
        assert "b.txt" in names
        assert "c.exe" not in names

    def test_skip_gitignore_files(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n")
        (tmp_path / "app.py").write_text("code")
        (tmp_path / "debug.log").write_text("log data")

        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "app.py" in names
        assert "debug.log" not in names

    def test_skip_hidden_dirs(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "secret.py").write_text("secret")
        (tmp_path / "visible.py").write_text("visible")

        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "visible.py" in names
        assert "secret.py" not in names

    def test_skip_node_modules(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "pkg.js").write_text("pkg")
        (tmp_path / "index.js").write_text("main")

        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "index.js" in names
        assert "pkg.js" not in names

    def test_include_filter(self, tmp_path):
        (tmp_path / "app.py").write_text("code")
        (tmp_path / "test.py").write_text("test")
        (tmp_path / "readme.md").write_text("docs")

        from rag.indexer import collect_files
        files = collect_files(str(tmp_path), include="*.py")
        names = [f.name for f in files]
        assert "app.py" in names
        assert "test.py" in names
        assert "readme.md" not in names

    def test_single_file(self, tmp_path):
        single = tmp_path / "only.py"
        single.write_text("code")

        from rag.indexer import collect_files
        files = collect_files(str(single))
        assert len(files) == 1
        assert files[0] == single

    def test_skip_large_files(self, tmp_path):
        small = tmp_path / "small.py"
        small.write_text("x" * 100)
        large = tmp_path / "large.py"
        large.write_text("x" * 200_000)

        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "small.py" in names
        assert "large.py" not in names

    def test_recursive_collect(self, tmp_path):
        sub = tmp_path / "src" / "deep"
        sub.mkdir(parents=True)
        (sub / "deep.py").write_text("deep code")
        (tmp_path / "root.py").write_text("root code")

        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "deep.py" in names
        assert "root.py" in names


# ─── index_directory (mocked ChromaDB) ────────────────────────────────────────
def _make_mock_chroma():
    mock_chroma = MagicMock()
    mock_settings = MagicMock()
    mock_chroma.config.Settings = mock_settings
    return mock_chroma


class TestIndexDirectory:
    def test_empty_directory(self, tmp_path):
        mock_chroma = _make_mock_chroma()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"metadatas": []}
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            from core.config import Config
            with patch("core.config.Path.home", return_value=tmp_path):
                config = Config()
            from rag.indexer import index_directory
            n_files, n_chunks = index_directory(str(tmp_path), config=config)
            assert n_files == 0
            assert n_chunks == 0
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_index_text_files(self, tmp_path):
        (tmp_path / "hello.py").write_text("print('hello')")

        mock_chroma = _make_mock_chroma()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"metadatas": []}
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            from core.config import Config
            with patch("core.config.Path.home", return_value=tmp_path):
                config = Config()
            from rag.indexer import index_directory
            n_files, n_chunks = index_directory(str(tmp_path), config=config)
            assert n_files == 1
            assert n_chunks >= 1
            mock_collection.upsert.assert_called()
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_differential_indexing_skips_unchanged(self, tmp_path):
        (tmp_path / "cached.py").write_text("cached code")

        mock_chroma = _make_mock_chroma()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mtime = os.path.getmtime(tmp_path / "cached.py")
        mock_collection.get.return_value = {
            "metadatas": [{"file": "cached.py", "mtime": mtime}]
        }
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            from core.config import Config
            with patch("core.config.Path.home", return_value=tmp_path):
                config = Config()
            from rag.indexer import index_directory
            n_files, n_chunks = index_directory(str(tmp_path), config=config)
            assert n_files == 0
            mock_collection.upsert.assert_not_called()
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_include_filter(self, tmp_path):
        (tmp_path / "app.py").write_text("code")
        (tmp_path / "data.csv").write_text("a,b,c")

        mock_chroma = _make_mock_chroma()
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"metadatas": []}
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            from core.config import Config
            with patch("core.config.Path.home", return_value=tmp_path):
                config = Config()
            from rag.indexer import index_directory
            n_files, n_chunks = index_directory(str(tmp_path), include="*.py", config=config)
            assert n_files == 1
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
