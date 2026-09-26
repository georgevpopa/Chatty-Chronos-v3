"""Tests for rag/indexer.py — RAG indexing (extended coverage)."""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── extract_pdf_text ─────────────────────────────────────────────────────────
class TestExtractPdfText:
    def test_extract_with_pypdf(self, tmp_path):
        """Extracts text from PDF using pypdf."""
        mock_pypdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pypdf.PdfReader.return_value = mock_reader

        old = sys.modules.get("pypdf")
        sys.modules["pypdf"] = mock_pypdf

        try:
            from rag.indexer import extract_pdf_text
            pdf_file = tmp_path / "test.pdf"
            pdf_file.write_bytes(b"%PDF-1.4 fake content")

            result = extract_pdf_text(pdf_file)
            assert "Page 1 content" in result
        finally:
            if old:
                sys.modules["pypdf"] = old
            else:
                sys.modules.pop("pypdf", None)

    def test_extract_empty_pdf(self, tmp_path):
        """Empty PDF returns empty string."""
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
            pdf_file = tmp_path / "empty.pdf"
            pdf_file.write_bytes(b"%PDF-1.4")

            result = extract_pdf_text(pdf_file)
            assert result == ""
        finally:
            if old:
                sys.modules["pypdf"] = old
            else:
                sys.modules.pop("pypdf", None)

    def test_extract_error_returns_empty(self, tmp_path):
        """Error reading PDF returns empty string."""
        mock_pypdf = MagicMock()
        mock_pypdf.PdfReader.side_effect = Exception("Corrupt PDF")

        old = sys.modules.get("pypdf")
        sys.modules["pypdf"] = mock_pypdf

        try:
            from rag.indexer import extract_pdf_text
            pdf_file = tmp_path / "bad.pdf"
            pdf_file.write_bytes(b"not a pdf")

            result = extract_pdf_text(pdf_file)
            assert result == ""
        finally:
            if old:
                sys.modules["pypdf"] = old
            else:
                sys.modules.pop("pypdf", None)


# ─── extract_docx_text ───────────────────────────────────────────────────────
class TestExtractDocxText:
    def test_extract_with_docx(self, tmp_path):
        """Extracts text from DOCX using python-docx."""
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
            docx_file = tmp_path / "test.docx"
            docx_file.write_bytes(b"fake docx content")

            result = extract_docx_text(docx_file)
            assert "First paragraph" in result
            assert "Second paragraph" in result
        finally:
            if old:
                sys.modules["docx"] = old
            else:
                sys.modules.pop("docx", None)

    def test_extract_error_returns_empty(self, tmp_path):
        """Error reading DOCX returns empty string."""
        mock_docx = MagicMock()
        mock_docx.Document.side_effect = Exception("Corrupt DOCX")

        old = sys.modules.get("docx")
        sys.modules["docx"] = mock_docx

        try:
            from rag.indexer import extract_docx_text
            docx_file = tmp_path / "bad.docx"
            docx_file.write_bytes(b"not a docx")

            result = extract_docx_text(docx_file)
            assert result == ""
        finally:
            if old:
                sys.modules["docx"] = old
            else:
                sys.modules.pop("docx", None)


# ─── index_directory (extended) ──────────────────────────────────────────────
class TestIndexDirectoryExtended:
    def test_no_chromadb_returns_zero(self, tmp_path):
        """Returns 0,0 when chromadb not installed."""
        import sys
        old = sys.modules.pop("chromadb", None)

        from rag.indexer import index_directory
        from core.config import Config
        config = Config()

        result = index_directory(str(tmp_path), config=config)
        assert result == (0, 0)

        if old:
            sys.modules["chromadb"] = old

    def test_empty_directory(self, tmp_path):
        """Empty directory returns 0,0."""
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
            from rag.indexer import index_directory
            from core.config import Config
            config = Config()
            n_files, n_chunks = index_directory(str(tmp_path), config=config)
            assert n_files == 0
            assert n_chunks == 0
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_indexes_text_files(self, tmp_path):
        """Indexes .py and .txt files."""
        (tmp_path / "code.py").write_text("print('hello')")
        (tmp_path / "notes.txt").write_text("Some notes here")

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

            assert n_files == 2
            assert n_chunks >= 2
            mock_collection.upsert.assert_called()
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_differential_indexing_skips_unchanged(self, tmp_path):
        """Files with same mtime are skipped."""
        (tmp_path / "cached.py").write_text("cached content")

        mock_chroma = MagicMock()
        mock_settings = MagicMock()
        mock_chroma.config.Settings = mock_settings
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        import os
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

            # File should be skipped (not upserted)
            assert n_files == 0
            mock_collection.upsert.assert_not_called()
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_include_filter(self, tmp_path):
        """Only files matching include pattern are indexed."""
        (tmp_path / "app.py").write_text("code")
        (tmp_path / "data.csv").write_text("a,b,c")

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
            n_files, n_chunks = index_directory(str(tmp_path), include="*.py", config=config)

            assert n_files == 1  # Only .py file
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_skip_binary_extensions(self, tmp_path):
        """Binary files (.exe, .dll, etc.) are skipped."""
        (tmp_path / "app.exe").write_bytes(b"\x00\x00")
        (tmp_path / "lib.dll").write_bytes(b"\x00\x00")
        (tmp_path / "code.py").write_text("valid")

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

            assert n_files == 1  # Only code.py
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_skip_large_files(self, tmp_path):
        """Files larger than MAX_FILE_SIZE are skipped."""
        large = tmp_path / "large.txt"
        large.write_text("x" * 200_000)  # > 100KB
        small = tmp_path / "small.txt"
        small.write_text("small content")

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

            assert n_files == 1  # Only small.txt
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_empty_content_skipped(self, tmp_path):
        """Files with empty/whitespace-only content are skipped."""
        (tmp_path / "empty.txt").write_text("   \n  \n  ")
        (tmp_path / "valid.py").write_text("print('hi')")

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

            assert n_files == 1  # Only valid.py
        finally:
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v


# ─── index_url (extended) ────────────────────────────────────────────────────
class TestIndexUrlExtended:
    def test_http_error_returns_zero(self, tmp_path):
        """Returns 0 when HTTP request fails."""
        import sys
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

        from bs4 import BeautifulSoup
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
