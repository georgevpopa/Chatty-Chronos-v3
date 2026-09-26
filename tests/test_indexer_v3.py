"""Extended tests for rag/indexer.py — differential indexing, PDF/DOCX, edge cases."""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── Differential indexing: delete existing chunks ────────────────────────────
class TestDifferentialIndexing:
    def test_modified_file_deletes_old_chunks(self, tmp_path):
        """When a file is modified, old chunks are deleted before re-indexing."""
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        # Simulate existing indexed file with old mtime
        mock_collection.get.return_value = {
            "metadatas": [{"file": "modified.py", "mtime": 1.0}]
        }

        # Create file with newer mtime
        (tmp_path / "modified.py").write_text("updated content")
        # Force a newer mtime
        os.utime(tmp_path / "modified.py", (2.0, 2.0))

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            from rag.indexer import index_directory
            from core.config import Config
            config = Config()
            n_files, n_chunks = index_directory(str(tmp_path), config=config)

            assert n_files == 1
            # collection.delete should have been called for the modified file
            mock_collection.delete.assert_called()
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_unmodified_file_skipped(self, tmp_path):
        """Files with same mtime are skipped."""
        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        (tmp_path / "cached.py").write_text("cached content")
        mtime = os.path.getmtime(tmp_path / "cached.py")

        mock_collection.get.return_value = {
            "metadatas": [{"file": "cached.py", "mtime": mtime}]
        }

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            from rag.indexer import index_directory
            from core.config import Config
            config = Config()
            n_files, n_chunks = index_directory(str(tmp_path), config=config)

            assert n_files == 0
            mock_collection.upsert.assert_not_called()
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v


# ─── PDF extraction ───────────────────────────────────────────────────────────
class TestPdfExtraction:
    def test_extract_pdf_success(self):
        """PDF extraction works when pypdf is installed."""
        mock_pypdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF content"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pypdf.PdfReader.return_value = mock_reader

        old = sys.modules.get("pypdf")
        sys.modules["pypdf"] = mock_pypdf

        try:
            from rag.indexer import extract_pdf_text
            from pathlib import Path
            result = extract_pdf_text(Path("/fake.pdf"))
            assert "PDF content" in result
        finally:
            if old:
                sys.modules["pypdf"] = old
            else:
                sys.modules.pop("pypdf", None)

    def test_extract_pdf_error(self):
        """PDF extraction returns empty on error."""
        mock_pypdf = MagicMock()
        mock_pypdf.PdfReader.side_effect = Exception("corrupt PDF")

        old = sys.modules.get("pypdf")
        sys.modules["pypdf"] = mock_pypdf

        try:
            from rag.indexer import extract_pdf_text
            from pathlib import Path
            result = extract_pdf_text(Path("/bad.pdf"))
            assert result == ""
        finally:
            if old:
                sys.modules["pypdf"] = old
            else:
                sys.modules.pop("pypdf", None)

    def test_extract_pdf_empty_pages(self):
        """PDF with empty pages returns empty string."""
        mock_pypdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pypdf.PdfReader.return_value = mock_reader

        old = sys.modules.get("pypdf")
        sys.modules["pypdf"] = mock_pypdf

        try:
            from rag.indexer import extract_pdf_text
            from pathlib import Path
            result = extract_pdf_text(Path("/empty.pdf"))
            assert result == ""
        finally:
            if old:
                sys.modules["pypdf"] = old
            else:
                sys.modules.pop("pypdf", None)


# ─── DOCX extraction ──────────────────────────────────────────────────────────
class TestDocxExtraction:
    def test_extract_docx_success(self):
        """DOCX extraction works when python-docx is installed."""
        mock_docx = MagicMock()
        mock_para1 = MagicMock()
        mock_para1.text = "First paragraph"
        mock_para2 = MagicMock()
        mock_para2.text = "Second paragraph"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_docx.Document.return_value = mock_doc

        old = sys.modules.get("docx")
        sys.modules["docx"] = mock_docx

        try:
            from rag.indexer import extract_docx_text
            from pathlib import Path
            result = extract_docx_text(Path("/fake.docx"))
            assert "First paragraph" in result
            assert "Second paragraph" in result
        finally:
            if old:
                sys.modules["docx"] = old
            else:
                sys.modules.pop("docx", None)

    def test_extract_docx_error(self):
        """DOCX extraction returns empty on error."""
        mock_docx = MagicMock()
        mock_docx.Document.side_effect = Exception("corrupt DOCX")

        old = sys.modules.get("docx")
        sys.modules["docx"] = mock_docx

        try:
            from rag.indexer import extract_docx_text
            from pathlib import Path
            result = extract_docx_text(Path("/bad.docx"))
            assert result == ""
        finally:
            if old:
                sys.modules["docx"] = old
            else:
                sys.modules.pop("docx", None)


# ─── collect_files edge cases ─────────────────────────────────────────────────
class TestCollectFilesEdge:
    def test_single_file_path(self, tmp_path):
        """Single file path returns just that file."""
        (tmp_path / "only.py").write_text("code")
        from rag.indexer import collect_files
        files = collect_files(str(tmp_path / "only.py"))
        assert len(files) == 1
        assert files[0].name == "only.py"

    def test_pdf_not_skipped_by_size(self, tmp_path):
        """PDF files use larger size limit (10MB)."""
        # Create a small PDF (under 10MB limit)
        (tmp_path / "small.pdf").write_bytes(b"%PDF-1.4 fake" * 100)
        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "small.pdf" in names

    def test_docx_not_skipped_by_size(self, tmp_path):
        """DOCX files use larger size limit (10MB)."""
        (tmp_path / "small.docx").write_bytes(b"fake docx" * 100)
        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "small.docx" in names

    def test_skip_build_dirs(self, tmp_path):
        """Build directories are skipped."""
        (tmp_path / "build").mkdir()
        (tmp_path / "build" / "out.js").write_text("built")
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist" / "bundle.js").write_text("bundled")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("source")

        from rag.indexer import collect_files
        files = collect_files(str(tmp_path))
        names = [f.name for f in files]
        assert "app.py" in names
        assert "out.js" not in names
        assert "bundle.js" not in names


# ─── index_directory edge cases ──────────────────────────────────────────────
class TestIndexDirectoryEdge:
    def test_empty_content_skipped(self, tmp_path):
        """Files with only whitespace are skipped."""
        (tmp_path / "empty.py").write_text("   \n  \n  ")

        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.get.return_value = {"metadatas": []}

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            from rag.indexer import index_directory
            from core.config import Config
            config = Config()
            n_files, n_chunks = index_directory(str(tmp_path), config=config)

            assert n_files == 0
            mock_collection.upsert.assert_not_called()
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_config_none_uses_default(self, tmp_path):
        """When config is None, default Config() is used."""
        (tmp_path / "test.py").write_text("code")

        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.get.return_value = {"metadatas": []}

        old_modules = {k: sys.modules.get(k) for k in ["chromadb", "chromadb.config"]}
        sys.modules["chromadb"] = mock_chroma
        sys.modules["chromadb.config"] = mock_chroma.config

        try:
            from rag.indexer import index_directory
            # Pass config=None to trigger default Config()
            n_files, n_chunks = index_directory(str(tmp_path), config=None)

            assert n_files == 1
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
