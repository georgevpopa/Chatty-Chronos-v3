"""Tests for cli/commands.py — slash commands REPL handler."""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


# ─── /help ────────────────────────────────────────────────────────────────────
class TestHelp:
    def test_help_outputs_table(self):
        from cli.commands import handle_command
        handle_command("/help")
        # Should not raise — just prints table


# ─── /model ───────────────────────────────────────────────────────────────────
class TestModelCommand:
    def test_show_model_llamacpp(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "llamacpp")
        state.config.set("model", "test.gguf")
        state.config.set("local_server_model", "E:\\models\\test.gguf")

        with patch("os.path.isdir", return_value=True), \
             patch("os.listdir", return_value=["test.gguf", "other.gguf"]), \
             patch("os.path.getsize", return_value=5_000_000_000):
            handle_command("/model")

    def test_show_model_ollama(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "ollama")
        state.config.set("model", "llama3.1")

        with patch("llm.ollama_provider.list_models", return_value=["llama3.1", "codellama"]):
            handle_command("/model")

    def test_show_model_cloud(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "nvidia")
        state.config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")

        handle_command("/model")

    def test_set_model_llamacpp_by_number(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "llamacpp")
        state.config.set("local_server_model", "E:\\models\\test.gguf")

        with patch("os.path.isdir", return_value=True), \
             patch("os.listdir", return_value=["model1.gguf", "model2.gguf"]), \
             patch("llm.server_manager.restart_with_model", return_value=True):
            handle_command("/model 1")

    def test_set_model_llamacpp_by_name(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "llamacpp")
        state.config.set("local_server_model", "E:\\models\\test.gguf")

        with patch("os.path.isdir", return_value=True), \
             patch("os.listdir", return_value=["qwen.gguf", "llama.gguf"]), \
             patch("llm.server_manager.restart_with_model", return_value=True):
            handle_command("/model qwen")

    def test_set_model_ollama(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "ollama")
        state.config.set("model", "old-model")

        handle_command("/model new-model")
        assert state.config.get("model") == "new-model"

    def test_set_model_cloud(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "nvidia")
        state.config.set("model", "old-model")

        handle_command("/model new-model")
        assert state.config.get("model") == "new-model"


# ─── /provider ────────────────────────────────────────────────────────────────
class TestProviderCommand:
    def test_show_provider(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "llamacpp")
        handle_command("/provider")

    def test_set_provider(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "ollama")

        with patch("llm.server_manager.start_local_server"):
            handle_command("/provider llamacpp")

        assert state.config.get("provider") == "llamacpp"


# ─── /clear ───────────────────────────────────────────────────────────────────
class TestClearCommand:
    def test_clear_resets_messages(self):
        from cli.commands import handle_command
        from core import state
        state.messages = [{"role": "user", "content": "old"}]

        handle_command("/clear")

        assert len(state.messages) == 1
        assert state.messages[0]["role"] == "system"


# ─── /history ─────────────────────────────────────────────────────────────────
class TestHistoryCommand:
    def test_history_shows_user_msgs(self):
        from cli.commands import handle_command
        from core import state
        state.messages = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "bye"},
        ]

        handle_command("/history")


# ─── /config ──────────────────────────────────────────────────────────────────
class TestConfigCommand:
    def test_show_config(self):
        from cli.commands import handle_command
        handle_command("/config")

    def test_set_config(self):
        from cli.commands import handle_command
        from core import state
        handle_command("/config provider ollama")
        assert state.config.get("provider") == "ollama"

    def test_get_config_key(self):
        from cli.commands import handle_command
        handle_command("/config provider")


# ─── /models ──────────────────────────────────────────────────────────────────
class TestModelsCommand:
    def test_models_llamacpp(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "llamacpp")
        state.config.set("model", "test.gguf")
        handle_command("/models")

    def test_models_ollama_with_models(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "ollama")
        state.config.set("model", "llama3.1")

        with patch("llm.ollama_provider.list_models", return_value=["llama3.1"]):
            handle_command("/models")

    def test_models_ollama_no_connection(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "ollama")

        with patch("llm.ollama_provider.list_models", return_value=[]):
            handle_command("/models")


# ─── /providers ───────────────────────────────────────────────────────────────
class TestProvidersCommand:
    def test_providers_shows_list(self):
        from cli.commands import handle_command
        handle_command("/providers")


# ─── /tools ───────────────────────────────────────────────────────────────────
class TestToolsCommand:
    def test_tools_shows_list(self):
        from cli.commands import handle_command
        handle_command("/tools")


# ─── /save, /load ─────────────────────────────────────────────────────────────
class TestSaveLoad:
    def test_save_session(self):
        from cli.commands import handle_command
        from core import state
        state.messages = [{"role": "user", "content": "test"}]

        with patch("cli.commands.save_session"):
            handle_command("/save")

    def test_load_session(self):
        from cli.commands import handle_command
        with patch("cli.commands.load_session", return_value=True):
            handle_command("/load")

    def test_load_no_session(self):
        from cli.commands import handle_command
        with patch("cli.commands.load_session", return_value=False):
            handle_command("/load")


# ─── /export ──────────────────────────────────────────────────────────────────
class TestExportCommand:
    def test_export_creates_file(self, tmp_path):
        from cli.commands import handle_command
        from core import state
        state.messages = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]

        export_file = str(tmp_path / "export.md")
        handle_command(f"/export {export_file}")

        assert (tmp_path / "export.md").exists()
        content = (tmp_path / "export.md").read_text()
        assert "hello" in content
        assert "hi there" in content

    def test_export_default_filename(self):
        from cli.commands import handle_command
        from core import state
        state.messages = [{"role": "user", "content": "test"}]

        with patch("pathlib.Path.write_text"):
            handle_command("/export")


# ─── /stats ───────────────────────────────────────────────────────────────────
class TestStatsCommand:
    def test_stats_shows_info(self):
        from cli.commands import handle_command
        from core import state
        state.messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        handle_command("/stats")


# ─── /memory ──────────────────────────────────────────────────────────────────
class TestMemoryCommand:
    def test_memory_empty(self):
        from cli.commands import handle_command
        from core import state
        state.memory = MagicMock()
        state.memory.facts = []
        handle_command("/memory")

    def test_memory_with_facts(self):
        from cli.commands import handle_command
        from core import state
        state.memory = MagicMock()
        state.memory.facts = ["fact1", "fact2"]
        handle_command("/memory")

    def test_memory_add(self):
        from cli.commands import handle_command
        from core import state
        state.memory = MagicMock()
        handle_command("/memory add test fact")
        state.memory.add.assert_called_once_with("test fact")

    def test_memory_clear(self):
        from cli.commands import handle_command
        from core import state
        state.memory = MagicMock()
        handle_command("/memory clear")
        state.memory.clear.assert_called_once()

    def test_memory_remove(self):
        from cli.commands import handle_command
        from core import state
        state.memory = MagicMock()
        state.memory.remove.return_value = True
        handle_command("/memory remove 0")
        state.memory.remove.assert_called_once_with(0)

    def test_memory_remove_invalid(self):
        from cli.commands import handle_command
        from core import state
        state.memory = MagicMock()
        handle_command("/memory remove abc")


# ─── /specs ───────────────────────────────────────────────────────────────────
class TestSpecsCommand:
    def test_specs_empty(self):
        from cli.commands import handle_command
        with patch("cli.commands.list_specs", return_value=[]):
            handle_command("/specs")

    def test_specs_with_results(self):
        from cli.commands import handle_command
        with patch("cli.commands.list_specs", return_value=[{"name": "feature-a", "files": ["req.md"]}]):
            handle_command("/specs")


# ─── /plugins ─────────────────────────────────────────────────────────────────
class TestPluginsCommand:
    def test_plugins_list_empty(self):
        from cli.commands import handle_command
        with patch("cli.commands.get_loaded_plugins", return_value=[]):
            handle_command("/plugins")

    def test_plugins_reload(self):
        from cli.commands import handle_command
        with patch("cli.commands.reload_plugins", return_value=3):
            handle_command("/plugins reload")


# ─── /agents ──────────────────────────────────────────────────────────────────
class TestAgentsCommand:
    def test_agents_list(self):
        from cli.commands import handle_command
        with patch("cli.commands.list_agents", return_value=[]):
            handle_command("/agents")

    def test_agents_register(self):
        from cli.commands import handle_command
        with patch("cli.commands.register_agent"):
            handle_command("/agents register test_agent A test agent")


# ─── /doctor ──────────────────────────────────────────────────────────────────
class TestDoctorCommand:
    def test_doctor_ollama(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "ollama")

        with patch("llm.ollama_provider.list_models", return_value=["llama3.1"]):
            handle_command("/doctor")

    def test_doctor_llamacpp(self):
        from cli.commands import handle_command
        from core import state
        state.config.set("provider", "llamacpp")

        with patch("llm.llamacpp_provider.is_available", return_value=True):
            handle_command("/doctor")


# ─── /logs ────────────────────────────────────────────────────────────────────
class TestLogsCommand:
    def test_logs_no_dir(self):
        from cli.commands import handle_command
        with patch("pathlib.Path.exists", return_value=False):
            handle_command("/logs")


# ─── /agent ───────────────────────────────────────────────────────────────────
class TestAgentCommand:
    def test_agent_no_task(self):
        from cli.commands import handle_command
        handle_command("/agent")

    def test_agent_with_task(self):
        from cli.commands import handle_command
        with patch("cli.commands.ReActAgent") as MockAgent:
            mock_agent = MagicMock()
            MockAgent.return_value = mock_agent
            handle_command("/agent do something")
            mock_agent.run.assert_called_once_with("do something")


# ─── Unknown command ──────────────────────────────────────────────────────────
class TestUnknownCommand:
    def test_unknown_shows_error(self):
        from cli.commands import handle_command
        handle_command("/unknown_command")


# ─── /paste ────────────────────────────────────────────────────────────────────
class TestPasteCommand:
    def test_paste_no_clipboard(self):
        from cli.commands import handle_command
        with patch.dict("sys.modules", {"pyperclip": None}):
            handle_command("/paste")

    def test_paste_empty_clipboard(self):
        from cli.commands import handle_command
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = ""
        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            handle_command("/paste")


# ─── /team ────────────────────────────────────────────────────────────────────
class TestTeamCommand:
    def test_team_runs_workflow(self):
        from cli.commands import handle_command
        from core import state
        state.messages = [{"role": "system", "content": "prompt"}]

        with patch("core.team.run_team_workflow", return_value="team result") as mock_team:
            handle_command("/team do something complex")
            mock_team.assert_called_once()