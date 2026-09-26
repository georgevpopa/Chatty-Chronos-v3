"""Tests for core/session.py — session save/load/list."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestSessionSaveLoad:
    def test_save_and_load_session(self, tmp_path):
        """Save a session and load it back."""
        with patch("core.session.state") as mock_state:
            mock_state.config.dir = tmp_path
            mock_state.messages_lock = MagicMock()
            mock_state.messages = [
                {"role": "system", "content": "prompt"},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ]
            mock_state.active_session_id = None
            mock_state.SYSTEM_PROMPT = "prompt"

            from core.session import save_session, load_session
            save_session()

            # Verify session.json was created
            assert (tmp_path / "session.json").exists()

            # Modify messages
            mock_state.messages.clear()
            mock_state.messages.append({"role": "system", "content": "prompt"})

            # Load session
            result = load_session()
            assert result is True
            # Should have loaded the non-system messages
            assert len(mock_state.messages) == 3  # system + user + assistant

    def test_load_nonexistent_session(self, tmp_path):
        """Loading a non-existent session returns False."""
        with patch("core.session.state") as mock_state:
            mock_state.config.dir = tmp_path
            mock_state.messages = []

            from core.session import load_session
            result = load_session()
            assert result is False

    def test_save_creates_sessions_folder(self, tmp_path):
        """Save creates the sessions directory."""
        with patch("core.session.state") as mock_state:
            mock_state.config.dir = tmp_path
            mock_state.messages_lock = MagicMock()
            mock_state.messages = [
                {"role": "user", "content": "test"},
            ]
            mock_state.active_session_id = "test_session_123"

            from core.session import save_session
            save_session(session_id="test_session_123")

            sessions_dir = tmp_path / "sessions"
            assert sessions_dir.exists()
            assert (sessions_dir / "session_test_session_123.json").exists()


class TestListSessions:
    def test_list_empty_sessions(self, tmp_path):
        """List sessions when none exist."""
        with patch("core.session.state") as mock_state:
            mock_state.config.dir = tmp_path

            from core.session import list_sessions
            results = list_sessions()
            assert results == []

    def test_list_with_default_session(self, tmp_path):
        """List sessions includes default session.json."""
        # Create a session file
        session_data = [{"role": "user", "content": "Hello world"}]
        (tmp_path / "session.json").write_text(json.dumps(session_data))

        with patch("core.session.state") as mock_state:
            mock_state.config.dir = tmp_path

            from core.session import list_sessions
            results = list_sessions()
            assert len(results) == 1
            assert results[0]["id"] == "default"
            assert "Hello world" in results[0]["title"]

    def test_list_with_named_sessions(self, tmp_path):
        """List sessions includes named sessions."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "session_123.json").write_text(
            json.dumps([{"role": "user", "content": "Test message"}])
        )

        with patch("core.session.state") as mock_state:
            mock_state.config.dir = tmp_path

            from core.session import list_sessions
            results = list_sessions()
            assert len(results) == 1
            assert results[0]["id"] == "123"
