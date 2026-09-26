import os
import tempfile
import pytest
from pathlib import Path
from hypothesis import given, strategies as st
from tools.filesystem import ReadFile, WriteFile, SearchReplace, ListDirectory, GlobSearch, Grep, MoveFile

def test_read_file_not_found(tmp_path):
    reader = ReadFile()
    result = reader.execute(str(tmp_path / "non_existent.txt"))
    assert "Error: File not found" in result

def test_write_read_file(tmp_path):
    writer = WriteFile()
    reader = ReadFile()
    file_path = str(tmp_path / "test.txt")
    
    writer.execute(file_path, "Hello World")
    result = reader.execute(file_path)
    assert result == "Hello World"

def test_list_directory(tmp_path):
    lister = ListDirectory()
    # Create some files
    (tmp_path / "file1.txt").write_text("1")
    (tmp_path / "dir1").mkdir()
    
    result = lister.execute(str(tmp_path))
    assert "file1.txt" in result
    assert "[DIR] dir1" in result

@given(content=st.text())
def test_write_read_idempotent(content):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "idempotent.txt")
        writer = WriteFile()
        reader = ReadFile()
        
        # Write once
        writer.execute(path, content)
        read1 = reader.execute(path)
        
        # Write again with the same content (idempotency check)
        writer.execute(path, content)
        read2 = reader.execute(path)
        
        # Because ReadFile truncates at 50,000 characters, handle that logic
        expected = content.replace('\r\n', '\n').replace('\r', '\n')
        actual1 = read1.replace('\r\n', '\n').replace('\r', '\n')
        actual2 = read2.replace('\r\n', '\n').replace('\r', '\n')

        if len(expected) > 50000:
            assert actual1.startswith(expected[:50000])
        else:
            assert actual1 == expected
            
        assert actual1 == actual2

def test_search_replace(tmp_path):
    writer = WriteFile()
    sr = SearchReplace()
    reader = ReadFile()
    
    file_path = str(tmp_path / "test_sr.txt")
    writer.execute(file_path, "apple banana apple")
    
    sr.execute(file_path, "apple", "orange")
    result = reader.execute(file_path)
    assert result == "orange banana orange"
