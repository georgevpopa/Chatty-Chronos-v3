"""Tests for main.py — REPL entry point."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestShowBanner:
    def test_llamacpp_connected(self):
        import main
        from core import state
        state.config.set("provider", "llamacpp")
        with patch("llm.llamacpp_provider.is_available", return_value=True):
            main.show_banner()

    def test_llamacpp_disconnected(self):
        import main
        from core import state
        state.config.set("provider", "llamacpp")
        with patch("llm.llamacpp_provider.is_available", return_value=False):
            main.show_banner()

    def test_ollama_connected(self):
        import main
        from core import state
        state.config.set("provider", "ollama")
        with patch("llm.ollama_provider.list_models", return_value=["llama3.1"]):
            main.show_banner()

    def test_ollama_disconnected(self):
        import main
        from core import state
        state.config.set("provider", "ollama")
        with patch("llm.ollama_provider.list_models", return_value=[]):
            main.show_banner()

    def test_cloud_active(self):
        import main
        from core import state
        state.config.set("provider", "nvidia")
        with patch("llm.fallback.get_available_providers", return_value=[
            {"name": "nvidia", "base_url": "https://integrate.api.nvidia.com/v1"}
        ]):
            main.show_banner()

    def test_cloud_not_configured(self):
        import main
        from core import state
        state.config.set("provider", "openrouter")
        with patch("llm.fallback.get_available_providers", return_value=[]):
            main.show_banner()


class TestMain:
    def test_exit_on_eof(self):
        """EOFError triggers handle_command('/exit') which calls sys.exit(0)."""
        import main
        mock_s = MagicMock()
        mock_s.prompt.side_effect = EOFError()
        mock_cmd = MagicMock()
        mock_cmd.side_effect = SystemExit(0)  # /exit exits
        with patch("sys.argv", ["main.py"]), \
             patch("main.show_banner"), \
             patch("main.send_message"), \
             patch("main.handle_command", mock_cmd), \
             patch("core.session.load_session", return_value=False), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(SystemExit):
                main.main(session=mock_s)

    def test_command_dispatched(self):
        """User types /help → handle_command('/help')."""
        import main
        mock_s = MagicMock()
        mock_s.prompt.side_effect = ["/help", EOFError()]
        mock_cmd = MagicMock()
        # First call (/help) returns None, second (/exit from EOFError) raises SystemExit
        mock_cmd.side_effect = [None, SystemExit(0)]
        with patch("sys.argv", ["main.py"]), \
             patch("main.show_banner"), \
             patch("main.send_message"), \
             patch("main.handle_command", mock_cmd), \
             patch("core.session.load_session", return_value=False), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(SystemExit):
                main.main(session=mock_s)
            mock_cmd.assert_any_call("/help")

    def test_message_dispatched(self):
        """Plain text → send_message(text)."""
        import main
        mock_s = MagicMock()
        mock_s.prompt.side_effect = ["hello", EOFError()]
        mock_send = MagicMock()
        mock_cmd = MagicMock()
        mock_cmd.side_effect = SystemExit(0)  # /exit exits
        with patch("sys.argv", ["main.py"]), \
             patch("main.show_banner"), \
             patch("main.send_message", mock_send), \
             patch("main.handle_command", mock_cmd), \
             patch("core.session.load_session", return_value=False), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(SystemExit):
                main.main(session=mock_s)
            mock_send.assert_called_once_with("hello")

    def test_empty_input_skipped(self):
        """Empty string → continue (no send_message)."""
        import main
        mock_s = MagicMock()
        mock_s.prompt.side_effect = ["", "", "done", EOFError()]
        mock_send = MagicMock()
        mock_cmd = MagicMock()
        mock_cmd.side_effect = SystemExit(0)  # only called for /exit
        with patch("sys.argv", ["main.py"]), \
             patch("main.show_banner"), \
             patch("main.send_message", mock_send), \
             patch("main.handle_command", mock_cmd), \
             patch("core.session.load_session", return_value=False), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(SystemExit):
                main.main(session=mock_s)
            mock_send.assert_called_once_with("done")

    def test_keyboard_interrupt_continues(self):
        """KeyboardInterrupt → print warning, continue loop."""
        import main
        calls = [0]
        def ps(*a):
            calls[0] += 1
            if calls[0] == 1:
                raise KeyboardInterrupt()
            raise EOFError()
        mock_s = MagicMock()
        mock_s.prompt.side_effect = ps
        mock_cmd = MagicMock()
        mock_cmd.side_effect = SystemExit(0)
        with patch("sys.argv", ["main.py"]), \
             patch("main.show_banner"), \
             patch("main.send_message"), \
             patch("main.handle_command", mock_cmd), \
             patch("core.session.load_session", return_value=False), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(SystemExit):
                main.main(session=mock_s)

    def test_web_mode(self):
        """--web flag → start_web_server, no REPL."""
        import main
        with patch("sys.argv", ["main.py", "--web"]), \
             patch("main.show_banner"), \
             patch("ui.web.start_web_server") as mock_web:
            main.main()
            mock_web.assert_called_once()

    def test_web_custom_port(self):
        import main
        with patch("sys.argv", ["main.py", "--web", "9999"]), \
             patch("main.show_banner"), \
             patch("ui.web.start_web_server") as mock_web:
            main.main()
            assert mock_web.call_args[0][1] == 9999

    def test_session_loaded(self):
        """If session.json exists → load_session() called."""
        import main
        mock_s = MagicMock()
        mock_s.prompt.side_effect = EOFError()
        mock_load = MagicMock()
        mock_cmd = MagicMock()
        mock_cmd.side_effect = SystemExit(0)
        with patch("sys.argv", ["main.py"]), \
             patch("main.show_banner"), \
             patch("main.send_message"), \
             patch("main.handle_command", mock_cmd), \
             patch("core.session.load_session", mock_load), \
             patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(SystemExit):
                main.main(session=mock_s)
            mock_load.assert_called_once()

    def test_llamacpp_starts_server(self):
        """llamacpp provider → start_local_server() called."""
        from core import state
        state.config.set("provider", "llamacpp")
        import main
        mock_s = MagicMock()
        mock_s.prompt.side_effect = EOFError()
        mock_start = MagicMock()
        mock_cmd = MagicMock()
        mock_cmd.side_effect = SystemExit(0)
        with patch("sys.argv", ["main.py"]), \
             patch("main.show_banner"), \
             patch("main.send_message"), \
             patch("main.handle_command", mock_cmd), \
             patch("llm.server_manager.start_local_server", mock_start), \
             patch("core.session.load_session", return_value=False), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(SystemExit):
                main.main(session=mock_s)
            mock_start.assert_called()

    def test_version(self):
        import main
        assert main.__version__ == "3.0.0"
