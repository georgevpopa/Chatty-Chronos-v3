"""Extended tests for tools/filesystem.py — full coverage of all tools."""
import os
import tempfile
import pytest
from pathlib import Path


# ─── ReadFile ─────────────────────────────────────────────────────────────────
class TestReadFile:
    def test_read_existing_file(self, tmp_path):
        (tmp_path / "test.txt").write_text("hello world")
        from tools.filesystem import ReadFile
        result = ReadFile().execute(str(tmp_path / "test.txt"))
        assert result == "hello world"

    def test_file_not_found(self, tmp_path):
        from tools.filesystem import ReadFile
        result = ReadFile().execute(str(tmp_path / "nonexistent.txt"))
        assert "Error: File not found" in result

    def test_not_a_file(self, tmp_path):
        from tools.filesystem import ReadFile
        result = ReadFile().execute(str(tmp_path))
        assert "Error: Not a file" in result

    def test_truncation(self, tmp_path):
        (tmp_path / "big.txt").write_text("x" * 60000)
        from tools.filesystem import ReadFile
        result = ReadFile().execute(str(tmp_path / "big.txt"))
        assert "Truncated" in result
        assert len(result) < 60000


# ─── WriteFile ────────────────────────────────────────────────────────────────
class TestWriteFile:
    def test_write_creates_file(self, tmp_path):
        from tools.filesystem import WriteFile
        result = WriteFile().execute(str(tmp_path / "new.txt"), "content")
        assert "Successfully wrote" in result
        assert (tmp_path / "new.txt").read_text() == "content"

    def test_append_mode(self, tmp_path):
        (tmp_path / "app.txt").write_text("first ")
        from tools.filesystem import WriteFile
        result = WriteFile().execute(str(tmp_path / "app.txt"), "second", mode="a")
        assert "mode: a" in result
        assert (tmp_path / "app.txt").read_text() == "first second"

    def test_creates_parent_dirs(self, tmp_path):
        from tools.filesystem import WriteFile
        result = WriteFile().execute(str(tmp_path / "deep" / "nested" / "file.txt"), "content")
        assert "Successfully wrote" in result
        assert (tmp_path / "deep" / "nested" / "file.txt").exists()

    def test_get_diff_new_file(self, tmp_path):
        from tools.filesystem import WriteFile
        diff = WriteFile().get_diff(str(tmp_path / "new.txt"), "new content")
        assert diff is not None
        assert "+new content" in diff

    def test_get_diff_existing_file(self, tmp_path):
        (tmp_path / "existing.txt").write_text("old content")
        from tools.filesystem import WriteFile
        diff = WriteFile().get_diff(str(tmp_path / "existing.txt"), "new content")
        assert diff is not None
        assert "-old content" in diff
        assert "+new content" in diff

    def test_get_diff_append_mode(self, tmp_path):
        (tmp_path / "app.txt").write_text("first ")
        from tools.filesystem import WriteFile
        diff = WriteFile().get_diff(str(tmp_path / "app.txt"), "second", mode="a")
        assert diff is not None
        assert "+second" in diff

    def test_get_diff_no_change(self, tmp_path):
        (tmp_path / "same.txt").write_text("content\n")
        from tools.filesystem import WriteFile
        diff = WriteFile().get_diff(str(tmp_path / "same.txt"), "content\n")
        assert diff is None


# ─── SearchReplace ────────────────────────────────────────────────────────────
class TestSearchReplace:
    def test_replace_found(self, tmp_path):
        (tmp_path / "test.txt").write_text("apple banana apple")
        from tools.filesystem import SearchReplace
        result = SearchReplace().execute(str(tmp_path / "test.txt"), "apple", "orange")
        assert "2 occurrence" in result
        assert (tmp_path / "test.txt").read_text() == "orange banana orange"

    def test_replace_not_found(self, tmp_path):
        (tmp_path / "test.txt").write_text("hello world")
        from tools.filesystem import SearchReplace
        result = SearchReplace().execute(str(tmp_path / "test.txt"), "xyz", "abc")
        assert "Text not found" in result

    def test_replace_file_not_found(self, tmp_path):
        from tools.filesystem import SearchReplace
        result = SearchReplace().execute(str(tmp_path / "nope.txt"), "a", "b")
        assert "File not found" in result

    def test_get_diff_found(self, tmp_path):
        (tmp_path / "test.txt").write_text("hello world")
        from tools.filesystem import SearchReplace
        diff = SearchReplace().get_diff(str(tmp_path / "test.txt"), "hello", "hi")
        assert diff is not None
        assert "-hello" in diff
        assert "+hi" in diff

    def test_get_diff_not_found(self, tmp_path):
        (tmp_path / "test.txt").write_text("hello world")
        from tools.filesystem import SearchReplace
        diff = SearchReplace().get_diff(str(tmp_path / "test.txt"), "xyz", "abc")
        assert diff is None

    def test_get_diff_file_not_exists(self, tmp_path):
        from tools.filesystem import SearchReplace
        diff = SearchReplace().get_diff(str(tmp_path / "nope.txt"), "a", "b")
        assert diff is None


# ─── ListDirectory ────────────────────────────────────────────────────────────
class TestListDirectory:
    def test_list_files(self, tmp_path):
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "subdir").mkdir()
        from tools.filesystem import ListDirectory
        result = ListDirectory().execute(str(tmp_path))
        assert "file.txt" in result
        assert "[DIR] subdir" in result

    def test_empty_directory(self, tmp_path):
        from tools.filesystem import ListDirectory
        result = ListDirectory().execute(str(tmp_path))
        assert "empty directory" in result

    def test_path_not_found(self, tmp_path):
        from tools.filesystem import ListDirectory
        result = ListDirectory().execute(str(tmp_path / "nonexistent"))
        assert "Path not found" in result

    def test_not_a_directory(self, tmp_path):
        (tmp_path / "file.txt").write_text("content")
        from tools.filesystem import ListDirectory
        result = ListDirectory().execute(str(tmp_path / "file.txt"))
        assert "Not a directory" in result


# ─── GlobSearch ────────────────────────────────────────────────────────────────
class TestGlobSearch:
    def test_find_files(self, tmp_path):
        (tmp_path / "test.py").write_text("code")
        from tools.filesystem import GlobSearch
        result = GlobSearch().execute("*.py", str(tmp_path))
        assert "test.py" in result
        assert "Found" in result

    def test_no_matches(self, tmp_path):
        from tools.filesystem import GlobSearch
        result = GlobSearch().execute("*.xyz", str(tmp_path))
        assert "No files matching" in result

    def test_recursive_pattern(self, tmp_path):
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "app.py").write_text("code")
        from tools.filesystem import GlobSearch
        result = GlobSearch().execute("**/*.py", str(tmp_path))
        assert "app.py" in result


# ─── Grep ─────────────────────────────────────────────────────────────────────
class TestGrep:
    def test_search_in_file(self, tmp_path):
        (tmp_path / "code.py").write_text("def hello():\n    pass\ndef world():\n    pass")
        from tools.filesystem import Grep
        result = Grep().execute("def", str(tmp_path / "code.py"))
        assert "2 match" in result
        assert "def hello" in result

    def test_search_in_directory(self, tmp_path):
        (tmp_path / "a.py").write_text("TODO fix this")
        (tmp_path / "b.py").write_text("no todos here")
        from tools.filesystem import Grep
        result = Grep().execute("TODO", str(tmp_path))
        assert "a.py" in result

    def test_no_matches(self, tmp_path):
        (tmp_path / "clean.py").write_text("clean code")
        from tools.filesystem import Grep
        result = Grep().execute("FIXME", str(tmp_path))
        assert "No matches" in result

    def test_path_not_found(self, tmp_path):
        from tools.filesystem import Grep
        result = Grep().execute("test", str(tmp_path / "nonexistent"))
        assert "Path not found" in result

    def test_include_filter(self, tmp_path):
        (tmp_path / "code.py").write_text("TODO in py")
        (tmp_path / "data.txt").write_text("TODO in txt")
        from tools.filesystem import Grep
        result = Grep().execute("TODO", str(tmp_path), include="*.py")
        assert "code.py" in result
        assert "data.txt" not in result

    def test_max_results(self, tmp_path):
        # Create file with many matches
        content = "\n".join([f"line {i} TODO" for i in range(60)])
        (tmp_path / "many.py").write_text(content)
        from tools.filesystem import Grep
        result = Grep().execute("TODO", str(tmp_path))
        assert "50 match" in result


# ─── MoveFile ─────────────────────────────────────────────────────────────────
class TestMoveFile:
    def test_move_file(self, tmp_path):
        (tmp_path / "src.txt").write_text("content")
        dst = tmp_path / "dest"
        from tools.filesystem import MoveFile
        result = MoveFile().execute(str(tmp_path / "src.txt"), str(dst))
        assert "Success" in result
        assert (dst / "src.txt").exists()
        assert not (tmp_path / "src.txt").exists()

    def test_creates_dest_dir(self, tmp_path):
        (tmp_path / "file.txt").write_text("content")
        dst = tmp_path / "new" / "deep" / "folder"
        from tools.filesystem import MoveFile
        result = MoveFile().execute(str(tmp_path / "file.txt"), str(dst))
        assert "Success" in result
        assert (dst / "file.txt").exists()

    def test_source_not_found(self, tmp_path):
        from tools.filesystem import MoveFile
        result = MoveFile().execute(str(tmp_path / "missing.txt"), str(tmp_path / "dest"))
        assert "does not exist" in result
