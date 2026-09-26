"""Tests for tools/human.py — human-in-the-loop tools."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── AskUser ──────────────────────────────────────────────────────────────────
class TestAskUser:
    def test_tool_creation(self):
        from tools.human import AskUser
        tool = AskUser()
        assert tool.name == "ask_user"
        assert tool.requires_permission is False

    def test_tool_schema(self):
        from tools.human import AskUser
        tool = AskUser()
        schema = tool.to_ollama_schema()
        assert schema["function"]["name"] == "ask_user"
        assert "question" in schema["function"]["parameters"]["properties"]

    @patch("tools.human.ask_user_prompt", return_value="I want dark theme")
    def test_execute_with_answer(self, mock_ask):
        from tools.human import AskUser
        tool = AskUser()
        result = tool.execute(question="What theme do you prefer?")

        assert "dark theme" in result
        assert "User replied" in result
        mock_ask.assert_called_once_with("What theme do you prefer?")

    @patch("tools.human.ask_user_prompt", return_value="")
    def test_execute_no_answer(self, mock_ask):
        from tools.human import AskUser
        tool = AskUser()
        result = tool.execute(question="Any preference?")

        assert "no answer" in result.lower()
        mock_ask.assert_called_once()

    @patch("tools.human.ask_user_prompt", return_value=None)
    def test_execute_none_answer(self, mock_ask):
        from tools.human import AskUser
        tool = AskUser()
        result = tool.execute(question="Question?")

        assert "no answer" in result.lower()
