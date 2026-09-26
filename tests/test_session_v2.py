"""Extended tests for core/session.py — full coverage of save/load/list."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── save_session ─────────────────────────────────────────────────────────────
class TestSaveSession:
    def test_save_creates_session_json(self, tmp_path):
        """save_session creates session.json with non-system messages."""
        import core.session as session_mod
        from core import state

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [
                {"role": "system", "content": "prompt"},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ]
            state.messages_lock = __import__("threading").RLock()
            state.active_session_id = None

            session_mod.save_session()

            session_file = tmp_path / "session.json"
            assert session_file.exists()
            data = json.loads(session_file.read_text())
            assert len(data) == 2  # system message excluded
            assert data[0]["role"] == "user"

    def test_save_creates_sessions_folder(self, tmp_path):
        """save_session creates sessions/ folder with named file."""
        import core.session as session_mod
        from core import state

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "user", "content": "test"}]
            state.messages_lock = __import__("threading").RLock()
            state.active_session_id = "test_123"

            session_mod.save_session(session_id="test_123")

            sessions_dir = tmp_path / "sessions"
            assert sessions_dir.exists()
            assert (sessions_dir / "session_test_123.json").exists()

    def test_save_auto_generates_session_id(self, tmp_path):
        """save_session auto-generates session_id if not provided."""
        import core.session as session_mod
        from core import state

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "user", "content": "test"}]
            state.messages_lock = __import__("threading").RLock()
            state.active_session_id = None

            session_mod.save_session()

            sessions_dir = tmp_path / "sessions"
            assert sessions_dir.exists()
            # Should have created a session file with a timestamp ID
            files = list(sessions_dir.glob("session_*.json"))
            assert len(files) == 1

    def test_save_with_existing_session_id(self, tmp_path):
        """save_session uses existing active_session_id."""
        import core.session as session_mod
        from core import state

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "user", "content": "test"}]
            state.messages_lock = __import__("threading").RLock()
            state.active_session_id = "existing_id"

            session_mod.save_session()

            sessions_dir = tmp_path / "sessions"
            assert (sessions_dir / "session_existing_id.json").exists()

    def test_save_exception_handled(self, tmp_path):
        """save_session handles write errors gracefully."""
        import core.session as session_mod
        from core import state

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "user", "content": "test"}]
            state.messages_lock = __import__("threading").RLock()
            state.active_session_id = None

            # Mock open to raise an error
            with patch("builtins.open", side_effect=IOError("Disk full")):
                session_mod.save_session()  # Should not raise


# ─── load_session ─────────────────────────────────────────────────────────────
class TestLoadSession:
    def test_load_default_session(self, tmp_path):
        """load_session loads from session.json."""
        import core.session as session_mod
        from core import state

        # Create session file
        session_data = [{"role": "user", "content": "hello"}]
        (tmp_path / "session.json").write_text(json.dumps(session_data))

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "system", "content": "prompt"}]
            state.messages_lock = __import__("threading").RLock()
            state.SYSTEM_PROMPT = "prompt"
            state.active_session_id = None

            result = session_mod.load_session()

            assert result is True
            assert len(state.messages) == 2  # system + loaded

    def test_load_named_session(self, tmp_path):
        """load_session loads from sessions/session_<id>.json."""
        import core.session as session_mod
        from core import state

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "session_myid.json").write_text(
            json.dumps([{"role": "user", "content": "named session"}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "system", "content": "prompt"}]
            state.messages_lock = __import__("threading").RLock()
            state.SYSTEM_PROMPT = "prompt"

            result = session_mod.load_session(session_id="myid")

            assert result is True
            assert state.active_session_id == "myid"

    def test_load_nonexistent_returns_false(self, tmp_path):
        """load_session returns False when file doesn't exist."""
        import core.session as session_mod
        from core import state

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "system", "content": "prompt"}]
            state.messages_lock = __import__("threading").RLock()
            state.SYSTEM_PROMPT = "prompt"
            state.active_session_id = None

            result = session_mod.load_session()
            assert result is False

    def test_load_clears_existing_messages(self, tmp_path):
        """load_session clears existing messages before loading."""
        import core.session as session_mod
        from core import state

        (tmp_path / "session.json").write_text(
            json.dumps([{"role": "user", "content": "loaded"}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [
                {"role": "system", "content": "old prompt"},
                {"role": "user", "content": "old message"},
                {"role": "assistant", "content": "old response"},
            ]
            state.messages_lock = __import__("threading").RLock()
            state.SYSTEM_PROMPT = "new prompt"
            state.active_session_id = None

            session_mod.load_session()

            # Should have system + loaded, old messages cleared
            assert len(state.messages) == 2
            assert state.messages[0]["content"] == "new prompt"

    def test_load_exception_returns_false(self, tmp_path):
        """load_session returns False on JSON parse error."""
        import core.session as session_mod
        from core import state

        (tmp_path / "session.json").write_text("not valid json {{{")

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "system", "content": "prompt"}]
            state.messages_lock = __import__("threading").RLock()
            state.SYSTEM_PROMPT = "prompt"
            state.active_session_id = None

            result = session_mod.load_session()
            assert result is False

    def test_load_resets_active_session_id(self, tmp_path):
        """load_session without session_id resets active_session_id."""
        import core.session as session_mod
        from core import state

        (tmp_path / "session.json").write_text(
            json.dumps([{"role": "user", "content": "test"}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            state.messages = [{"role": "system", "content": "prompt"}]
            state.messages_lock = __import__("threading").RLock()
            state.SYSTEM_PROMPT = "prompt"
            state.active_session_id = "old_id"

            session_mod.load_session()
            assert state.active_session_id is None


# ─── list_sessions ────────────────────────────────────────────────────────────
class TestListSessions:
    def test_list_empty(self, tmp_path):
        """list_sessions returns empty when no sessions exist."""
        import core.session as session_mod
        from core import state

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            result = session_mod.list_sessions()
            assert result == []

    def test_list_default_session(self, tmp_path):
        """list_sessions includes default session.json."""
        import core.session as session_mod
        from core import state

        (tmp_path / "session.json").write_text(
            json.dumps([{"role": "user", "content": "Hello world"}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            result = session_mod.list_sessions()

        assert len(result) == 1
        assert result[0]["id"] == "default"
        assert "Hello world" in result[0]["title"]

    def test_list_named_sessions(self, tmp_path):
        """list_sessions includes named sessions."""
        import core.session as session_mod
        from core import state

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "session_abc123.json").write_text(
            json.dumps([{"role": "user", "content": "Test message"}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            result = session_mod.list_sessions()

        assert len(result) == 1
        assert result[0]["id"] == "abc123"
        assert "Test message" in result[0]["title"]

    def test_list_sorted_by_mtime(self, tmp_path):
        """Sessions are sorted by modification time descending."""
        import core.session as session_mod
        from core import state
        import time

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        # Create two sessions with different mtimes
        (sessions_dir / "session_old.json").write_text(
            json.dumps([{"role": "user", "content": "old"}])
        )
        time.sleep(0.1)
        (sessions_dir / "session_new.json").write_text(
            json.dumps([{"role": "user", "content": "new"}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            result = session_mod.list_sessions()

        # Newest first — ID is filename without session_ prefix
        assert result[0]["id"] == "new"
        assert result[1]["id"] == "old"

    def test_list_title_truncation(self, tmp_path):
        """Long titles are truncated to 30 chars."""
        import core.session as session_mod
        from core import state

        long_title = "A" * 50
        (tmp_path / "session.json").write_text(
            json.dumps([{"role": "user", "content": long_title}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            result = session_mod.list_sessions()

        assert len(result[0]["title"]) <= 33  # 30 + "..."

    def test_list_empty_chat_title(self, tmp_path):
        """Empty chat gets 'Empty Chat' title."""
        import core.session as session_mod
        from core import state

        (tmp_path / "session.json").write_text(
            json.dumps([{"role": "assistant", "content": "no user messages"}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            result = session_mod.list_sessions()

        assert result[0]["title"] == "Empty Chat"

    def test_list_corrupt_file_skipped(self, tmp_path):
        """Corrupt session files are skipped gracefully."""
        import core.session as session_mod
        from core import state

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "session_bad.json").write_text("not json")
        (sessions_dir / "session_good.json").write_text(
            json.dumps([{"role": "user", "content": "good"}])
        )

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            result = session_mod.list_sessions()

        # Only good session should appear — ID is filename without session_ prefix
        assert len(result) == 1
        assert result[0]["id"] == "good"

    def test_list_default_corrupt_skipped(self, tmp_path):
        """Corrupt default session.json is skipped."""
        import core.session as session_mod
        from core import state

        (tmp_path / "session.json").write_text("not json")

        with patch.object(state, "config") as mock_config:
            mock_config.dir = tmp_path
            result = session_mod.list_sessions()

        assert result == []
