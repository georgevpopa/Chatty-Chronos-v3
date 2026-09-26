"""Filesystem tools — read, write, search_replace, list_directory, glob, move_file."""
import os
import shutil
import glob as glob_module
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
from tools.base import Tool


class ReadFileSchema(BaseModel):
    path: str = Field(..., description="Path to the file to read")

class ReadFile(Tool):
    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read the contents of a file. Returns the full text content.",
            input_schema=ReadFileSchema,
            requires_permission=False,
        )

    def execute(self, path: str, **kwargs) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: File not found: {p}"
        if not p.is_file():
            return f"Error: Not a file: {p}"
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if len(content) > 50000:
                return content[:50000] + f"\n\n[Truncated — file is {len(content)} chars]"
            return content
        except Exception as e:
            return f"Error reading file: {e}"


class WriteFileSchema(BaseModel):
    path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write")
    mode: str = Field(default="w", description="Mode: 'w' for overwrite (default), 'a' for append")

class WriteFile(Tool):
    def __init__(self):
        super().__init__(
            name="write_file",
            description="Create, overwrite, or append content to a file.",
            input_schema=WriteFileSchema,
            requires_permission=True,
        )

    def execute(self, path: str, content: str, mode: str = "w", **kwargs) -> str:
        p = Path(path).expanduser().resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            write_mode = "a" if mode == "a" else "w"
            with open(p, write_mode, encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} chars to {p} (mode: {write_mode})"
        except Exception as e:
            return f"Error writing file: {e}"

    def get_diff(self, path: str, content: str, mode: str = "w", **kwargs) -> Optional[str]:
        import difflib
        p = Path(path).expanduser().resolve()
        
        old_lines = []
        if p.exists() and p.is_file():
            try:
                old_lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
            except Exception:
                pass  # Ignore binary files or read errors
        
        if mode == "a":
            new_lines = old_lines + content.splitlines(keepends=True)
        else:
            new_lines = content.splitlines(keepends=True)
            if content and not content.endswith("\n"):
                new_lines[-1] = new_lines[-1] + "\n\\ No newline at end of file\n"
        
        diff = "".join(difflib.unified_diff(
            old_lines, new_lines, 
            fromfile=str(p), tofile=str(p)
        ))
        return diff if diff else None


class SearchReplaceSchema(BaseModel):
    path: str = Field(..., description="Path to the file")
    old_text: str = Field(..., description="Exact text to find")
    new_text: str = Field(..., description="Replacement text")

class SearchReplace(Tool):
    def __init__(self):
        super().__init__(
            name="search_replace",
            description="Replace an exact string in a file. Safer than full rewrite.",
            input_schema=SearchReplaceSchema,
            requires_permission=True,
        )

    def execute(self, path: str, old_text: str, new_text: str, **kwargs) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: File not found: {p}"
        content = p.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {p.name}"
        count = content.count(old_text)
        new_content = content.replace(old_text, new_text)
        p.write_text(new_content, encoding="utf-8")
        return f"Replaced {count} occurrence(s) in {p.name}"

    def get_diff(self, path: str, old_text: str, new_text: str, **kwargs) -> Optional[str]:
        import difflib
        p = Path(path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return None
        
        try:
            content = p.read_text(encoding="utf-8")
            if old_text not in content:
                return None
            new_content = content.replace(old_text, new_text)
            
            old_lines = content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            
            diff = "".join(difflib.unified_diff(
                old_lines, new_lines,
                fromfile=str(p), tofile=str(p)
            ))
            return diff if diff else None
        except Exception:
            return None


class ListDirectorySchema(BaseModel):
    path: str = Field(..., description="Directory path to list")

class ListDirectory(Tool):
    def __init__(self):
        super().__init__(
            name="list_directory",
            description="List files and directories at the given path.",
            input_schema=ListDirectorySchema,
            requires_permission=False,
        )

    def execute(self, path: str, **kwargs) -> str:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: Path not found: {p}"
        if not p.is_dir():
            return f"Error: Not a directory: {p}"
        entries = []
        try:
            for item in sorted(p.iterdir()):
                prefix = "[DIR] " if item.is_dir() else "      "
                entries.append(f"{prefix}{item.name}")
            if not entries:
                return f"{p}: (empty directory)"
            return f"{p}:\n" + "\n".join(entries[:100])
        except Exception as e:
            return f"Error listing directory: {e}"


class GlobSearchSchema(BaseModel):
    pattern: str = Field(..., description="Glob pattern")
    path: str = Field(default=".", description="Base directory (default: current dir)")

class GlobSearch(Tool):
    def __init__(self):
        super().__init__(
            name="glob_search",
            description="Find files matching a glob pattern (e.g. '**/*.py').",
            input_schema=GlobSearchSchema,
            requires_permission=False,
        )

    def execute(self, pattern: str, path: str = ".", **kwargs) -> str:
        base = Path(path).expanduser().resolve()
        matches = list(base.glob(pattern))[:50]
        if not matches:
            return f"No files matching '{pattern}' in {base}"
        result = f"Found {len(matches)} file(s):\n"
        result += "\n".join(f"  {m.relative_to(base)}" for m in matches)
        return result


class GrepSchema(BaseModel):
    pattern: str = Field(..., description="Text pattern to search for")
    path: str = Field(..., description="Directory or file to search in")
    include: Optional[str] = Field(default=None, description="File glob filter (e.g. '*.py')")

class Grep(Tool):
    def __init__(self):
        super().__init__(
            name="grep",
            description="Search for a text pattern in files. Returns matching lines with file:line format.",
            input_schema=GrepSchema,
            requires_permission=False,
        )

    def execute(self, pattern: str, path: str = ".", include: str = None, **kwargs) -> str:
        base = Path(path).expanduser().resolve()
        if base.is_file():
            files = [base]
        elif base.is_dir():
            glob_pat = include or "*"
            files = list(base.rglob(glob_pat))[:200]
        else:
            return f"Error: Path not found: {base}"

        results = []
        for f in files:
            if not f.is_file():
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    if pattern.lower() in line.lower():
                        rel = f.relative_to(base) if base.is_dir() else f.name
                        results.append(f"{rel}:{i}: {line.strip()}")
                        if len(results) >= 50:
                            break
            except Exception:
                continue
            if len(results) >= 50:
                break

        if not results:
            return f"No matches for '{pattern}' in {base}"
        return f"Found {len(results)} match(es):\n" + "\n".join(results)


class MoveFileSchema(BaseModel):
    src_path: str = Field(..., description="Absolute or relative path to the source file")
    dst_folder: str = Field(..., description="The destination directory where the file should be moved")

class MoveFile(Tool):
    def __init__(self):
        super().__init__(
            name="move_file",
            description="Move or rename a file or directory on Windows. Automatically creates missing target folders.",
            input_schema=MoveFileSchema,
            requires_permission=True,
        )

    def execute(self, src_path: str, dst_folder: str, **kwargs) -> str:
        src = Path(src_path).expanduser().resolve()
        dst_dir = Path(dst_folder).expanduser().resolve()

        if not src.exists():
            return f"Error: Source path does not exist: {src}"

        try:
            if not dst_dir.exists():
                dst_dir.mkdir(parents=True, exist_ok=True)
            
            final_dst = dst_dir / src.name
            shutil.move(str(src), str(final_dst))
            return f"Success: Moved '{src.name}' into '{dst_dir}'"
        except Exception as e:
            return f"Error executing move_file: {str(e)}"