"""Plugin loader — scans plugin directory and loads all valid plugins with manifests."""
import importlib.util
import sys
import json
from pathlib import Path
from rich.console import Console
from plugins.base import Plugin

console = Console()

PLUGINS_DIR = Path.home() / ".chatty-chronos" / "plugins"

_loaded_plugins: list[Plugin] = []


def load_plugins() -> list[Plugin]:
    """Scan plugins directory and load all valid plugins with manifests."""
    global _loaded_plugins
    _loaded_plugins = []

    if not PLUGINS_DIR.exists():
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        return []

    # Iterate over plugin folders
    for plugin_folder in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_folder.is_dir() or plugin_folder.name.startswith("_"):
            continue
            
        manifest_path = plugin_folder / "plugin.json"
        py_file = plugin_folder / "main.py"
        
        if not manifest_path.exists() or not py_file.exists():
            console.print(f"  [yellow]Skipping {plugin_folder.name}: Missing plugin.json or main.py[/yellow]")
            continue
            
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                
            plugin = _load_plugin_file(py_file, plugin_folder.name)
            if plugin:
                plugin.manifest = manifest  # Attach manifest to plugin instance
                # Check requested capabilities
                caps = manifest.get("capabilities", [])
                plugin.capabilities = caps
                
                plugin.on_load()
                _loaded_plugins.append(plugin)
        except Exception as e:
            console.print(f"  [red]Plugin error ({plugin_folder.name}): {e}[/red]")

    return _loaded_plugins


def _load_plugin_file(path: Path, plugin_id: str) -> Plugin | None:
    """Load a single plugin file and find the Plugin subclass."""
    module_name = f"chatty_plugin_{plugin_id}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # Find the Plugin subclass
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (isinstance(attr, type) and issubclass(attr, Plugin)
                and attr is not Plugin):
            return attr()

    return None


def get_loaded_plugins() -> list[Plugin]:
    """Return currently loaded plugins."""
    return _loaded_plugins


def get_plugin_commands() -> dict[str, Plugin]:
    """Return mapping of command -> plugin for all loaded plugins."""
    commands = {}
    for plugin in _loaded_plugins:
        for cmd in plugin.commands:
            commands[cmd] = plugin
    return commands


def reload_plugins() -> int:
    """Unload all plugins and reload from disk."""
    for p in _loaded_plugins:
        try:
            p.on_unload()
        except Exception:
            pass
    plugins = load_plugins()
    return len(plugins)
