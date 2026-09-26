"""Tests for tools/memory_tools.py — store and search memory tools."""
import json
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── StoreMemory ──────────────────────────────────────────────────────────────
class TestStoreMemory:
    def test_tool_creation(self):
        from tools.memory_tools import StoreMemory
        tool = StoreMemory()
        assert tool.name == "store_memory"
        assert tool.requires_permission is False

    def test_tool_schema(self):
        from tools.memory_tools import StoreMemory
        tool = StoreMemory()
        schema = tool.to_ollama_schema()
        assert schema["function"]["name"] == "store_memory"
        assert "key" in schema["function"]["parameters"]["properties"]
        assert "content" in schema["function"]["parameters"]["properties"]

    @patch("tools.memory_tools.store_memory", return_value=True)
    def test_execute_success(self, mock_store):
        from tools.memory_tools import StoreMemory
        tool = StoreMemory()
        result = tool.execute(key="test_key", content="test content")

        assert "Successfully" in result
        assert "test_key" in result
        mock_store.assert_called_once_with("test_key", "test content")

    @patch("tools.memory_tools.store_memory", return_value=False)
    def test_execute_failure(self, mock_store):
        from tools.memory_tools import StoreMemory
        tool = StoreMemory()
        result = tool.execute(key="test_key", content="test content")

        assert "Failed" in result


# ─── SearchMemory ─────────────────────────────────────────────────────────────
class TestSearchMemory:
    def test_tool_creation(self):
        from tools.memory_tools import SearchMemory
        tool = SearchMemory()
        assert tool.name == "search_memory"
        assert tool.requires_permission is False

    def test_tool_schema(self):
        from tools.memory_tools import SearchMemory
        tool = SearchMemory()
        schema = tool.to_ollama_schema()
        assert schema["function"]["name"] == "search_memory"
        assert "query" in schema["function"]["parameters"]["properties"]

    @patch("tools.memory_tools.search_memory", return_value=[])
    def test_execute_no_results(self, mock_search):
        from tools.memory_tools import SearchMemory
        tool = SearchMemory()
        result = tool.execute(query="nonexistent")

        assert "No relevant memories" in result

    @patch("tools.memory_tools.search_memory")
    def test_execute_with_results(self, mock_search):
        mock_search.return_value = [
            {"content": "User prefers dark theme", "metadata": {"key": "theme"}},
            {"content": "Project uses pytest", "metadata": {"key": "testing"}},
        ]

        from tools.memory_tools import SearchMemory
        tool = SearchMemory()
        result = tool.execute(query="theme")

        assert "Found memories" in result
        assert "dark theme" in result
        assert "theme" in result
        assert "testing" in result

    @patch("tools.memory_tools.search_memory")
    def test_execute_single_result(self, mock_search):
        mock_search.return_value = [
            {"content": "Important fact", "metadata": {"key": "fact1"}},
        ]

        from tools.memory_tools import SearchMemory
        tool = SearchMemory()
        result = tool.execute(query="fact")

        assert "[1]" in result
        assert "Important fact" in result
        assert "fact1" in result

    @patch("tools.memory_tools.search_memory")
    def test_execute_missing_metadata_key(self, mock_search):
        """Results without metadata key still work."""
        mock_search.return_value = [
            {"content": "Some content", "metadata": {}},
        ]

        from tools.memory_tools import SearchMemory
        tool = SearchMemory()
        result = tool.execute(query="content")

        assert "Some content" in result
        assert "unknown" in result

    @patch("tools.memory_tools.search_memory")
    def test_execute_missing_content(self, mock_search):
        """Results without content field still work."""
        mock_search.return_value = [
            {"metadata": {"key": "k1"}},
        ]

        from tools.memory_tools import SearchMemory
        tool = SearchMemory()
        result = tool.execute(query="test")

        assert "[1]" in result
