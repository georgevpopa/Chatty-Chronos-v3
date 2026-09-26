"""Tests for plugins/loader.py and plugins/base.py — plugin system."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── Plugin Base Class ────────────────────────────────────────────────────────
class TestPluginBase:
    def test_default_values(self):
        from plugins.base import Plugin
        plugin = Plugin()
        assert plugin.name == "unnamed"
        assert plugin.description == ""
        assert plugin.version == "0.1.0"
        assert plugin.commands == {}
        assert plugin.tools == []

    def test_get_tools_empty(self):
        from plugins.base import Plugin
        plugin = Plugin()
        assert plugin.get_tools() == []

    def test_get_tools_returns_list(self):
        from plugins.base import Plugin
        mock_tool = MagicMock()
        plugin = Plugin()
        plugin.tools = [mock_tool]
        assert plugin.get_tools() == [mock_tool]

    def test_handle_command_returns_none(self):
        from plugins.base import Plugin
        plugin = Plugin()
        result = plugin.handle_command("/test", "arg")
        assert result is None

    def test_on_load_no_error(self):
        from plugins.base import Plugin
        plugin = Plugin()
        plugin.on_load()  # Should not raise

    def test_on_unload_no_error(self):
        from plugins.base import Plugin
        plugin = Plugin()
        plugin.on_unload()  # Should not raise

    def test_on_message_no_error(self):
        from plugins.base import Plugin
        plugin = Plugin()
        plugin.on_message("user", "hello")  # Should not raise

    def test_custom_plugin_with_commands(self):
        from plugins.base import Plugin
        class MyPlugin(Plugin):
            name = "my_plugin"
            commands = {"/hello": "Say hello"}
            def handle_command(self, command, arg):
                if command == "/hello":
                    return f"Hello, {arg or 'world'}!"
                return None

        plugin = MyPlugin()
        assert plugin.name == "my_plugin"
        assert "/hello" in plugin.commands
        assert plugin.handle_command("/hello", "Alice") == "Hello, Alice!"
        assert plugin.handle_command("/other", "") is None


# ─── Plugin Loader ────────────────────────────────────────────────────────────
class TestPluginLoader:
    def test_empty_plugins_dir(self, tmp_path):
        """When plugins dir doesn't exist, it's created and returns empty."""
        plugins_dir = tmp_path / "plugins"
        # Don't create it — loader should create it

        from plugins.loader import load_plugins
        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            plugins = load_plugins()

        assert plugins == []
        assert plugins_dir.exists()

    def test_skip_directories_without_manifest(self, tmp_path):
        """Directories without plugin.json or main.py are skipped."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        (plugins_dir / "incomplete_plugin").mkdir()
        # No plugin.json or main.py

        from plugins.loader import load_plugins
        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            plugins = load_plugins()

        assert plugins == []

    def test_skip_hidden_directories(self, tmp_path):
        """Directories starting with _ are skipped."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        hidden = plugins_dir / "_hidden_plugin"
        hidden.mkdir()
        (hidden / "plugin.json").write_text("{}")
        (hidden / "main.py").write_text("x = 1")

        from plugins.loader import load_plugins
        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            plugins = load_plugins()

        assert plugins == []

    def test_skip_non_directories(self, tmp_path):
        """Non-directory items are skipped."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        (plugins_dir / "random_file.txt").write_text("not a plugin")

        from plugins.loader import load_plugins
        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            plugins = load_plugins()

        assert plugins == []

    def test_load_valid_plugin(self, tmp_path):
        """Valid plugin folder with manifest and main.py is loaded."""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "test_plugin"
        plugin_dir.mkdir(parents=True)

        # Create manifest
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "capabilities": ["commands"]
        }))

        # Create plugin file
        (plugin_dir / "main.py").write_text("""
from plugins.base import Plugin

class TestPlugin(Plugin):
    name = "test_plugin"
    version = "1.0.0"
    description = "A test plugin"
    commands = {"/test": "Run test"}

    def handle_command(self, command, arg):
        if command == "/test":
            return "Test executed!"
        return None
""")

        from plugins.loader import load_plugins
        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            plugins = load_plugins()

        assert len(plugins) == 1
        assert plugins[0].name == "test_plugin"
        assert plugins[0].manifest["name"] == "test_plugin"
        assert plugins[0].handle_command("/test", "") == "Test executed!"

    def test_plugin_without_plugin_subclass(self, tmp_path):
        """Plugin file without Plugin subclass is skipped."""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "no_class"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.json").write_text(json.dumps({"name": "no_class"}))
        (plugin_dir / "main.py").write_text("x = 1\n")

        from plugins.loader import load_plugins
        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            plugins = load_plugins()

        assert plugins == []

    def test_plugin_with_capabilities(self, tmp_path):
        """Plugin capabilities from manifest are attached."""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "cap_plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.json").write_text(json.dumps({
            "name": "cap_plugin",
            "capabilities": ["commands", "tools", "hooks"]
        }))
        (plugin_dir / "main.py").write_text("""
from plugins.base import Plugin
class CapPlugin(Plugin):
    name = "cap_plugin"
""")

        from plugins.loader import load_plugins
        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            plugins = load_plugins()

        assert len(plugins) == 1
        assert plugins[0].capabilities == ["commands", "tools", "hooks"]

    def test_plugin_load_error(self, tmp_path):
        """Plugin with syntax error is skipped gracefully."""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "broken"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.json").write_text(json.dumps({"name": "broken"}))
        (plugin_dir / "main.py").write_text("def invalid python syntax!!!")

        from plugins.loader import load_plugins
        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            plugins = load_plugins()

        assert plugins == []


# ─── get_loaded_plugins ───────────────────────────────────────────────────────
class TestGetLoadedPlugins:
    def test_returns_loaded_list(self, tmp_path):
        from plugins.loader import _loaded_plugins, get_loaded_plugins
        _loaded_plugins.clear()
        mock_plugin = MagicMock()
        _loaded_plugins.append(mock_plugin)

        result = get_loaded_plugins()
        assert result == [mock_plugin]

        _loaded_plugins.clear()


# ─── get_plugin_commands ──────────────────────────────────────────────────────
class TestGetPluginCommands:
    def test_commands_mapped(self):
        from plugins.loader import _loaded_plugins, get_plugin_commands
        _loaded_plugins.clear()

        mock_plugin = MagicMock()
        mock_plugin.commands = {"/hello": "Say hello", "/bye": "Say bye"}
        _loaded_plugins.append(mock_plugin)

        result = get_plugin_commands()
        assert "/hello" in result
        assert "/bye" in result
        assert result["/hello"] is mock_plugin

        _loaded_plugins.clear()

    def test_empty_commands(self):
        from plugins.loader import _loaded_plugins, get_plugin_commands
        _loaded_plugins.clear()

        mock_plugin = MagicMock()
        mock_plugin.commands = {}
        _loaded_plugins.append(mock_plugin)

        result = get_plugin_commands()
        assert result == {}

        _loaded_plugins.clear()


# ─── reload_plugins ───────────────────────────────────────────────────────────
class TestReloadPlugins:
    def test_reload_returns_count(self, tmp_path):
        """reload_plugins returns the count of loaded plugins."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir(parents=True)

        # Create a valid plugin folder
        plugin_dir = plugins_dir / "myplugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(json.dumps({"name": "myplugin"}))
        (plugin_dir / "main.py").write_text(
            "from plugins.base import Plugin\n"
            "class MyPlugin(Plugin):\n"
            "    name = 'myplugin'\n"
        )

        from plugins.loader import reload_plugins

        with patch("plugins.loader.PLUGINS_DIR", plugins_dir):
            count = reload_plugins()

        assert count >= 1

    def test_reload_calls_on_unload(self):
        """reload_plugins calls on_unload on previously loaded plugins."""
        from plugins.loader import _loaded_plugins, reload_plugins

        fake = MagicMock()
        fake.on_unload = MagicMock()
        _loaded_plugins.clear()
        _loaded_plugins.append(fake)

        # Mock load_plugins to return empty list (simulate no plugins found)
        with patch("plugins.loader.load_plugins", return_value=[]):
            count = reload_plugins()

        fake.on_unload.assert_called_once()
        assert count == 0
        _loaded_plugins.clear()
