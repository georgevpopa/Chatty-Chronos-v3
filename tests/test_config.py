"""Tests for core/config.py — configuration manager."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from core.config import Config, AppConfigSchema


@pytest.fixture
def config_dir(tmp_path):
    """Provide a temporary config directory."""
    with patch("core.config.Path.home", return_value=tmp_path):
        yield tmp_path


class TestConfig:
    def test_default_config_loaded(self, config_dir):
        """Config loads defaults when no file exists."""
        config = Config()
        assert config.get("provider") == "ollama"
        assert config.get("model") == ""

    def test_get_with_default(self, config_dir):
        """get() returns default for missing keys."""
        config = Config()
        assert config.get("nonexistent_key", "fallback") == "fallback"
        assert config.get("nonexistent_key") is None

    def test_set_and_get(self, config_dir):
        """set() persists value and get() retrieves it (using schema fields)."""
        config = Config()
        config.set("provider", "ollama")
        assert config.get("provider") == "ollama"

    def test_set_persists_to_file(self, config_dir):
        """set() writes to config.json on disk."""
        config = Config()
        config.set("provider", "llamacpp")

        with open(config.path, "r") as f:
            data = json.load(f)
        assert data["provider"] == "llamacpp"

    def test_save_and_reload(self, config_dir):
        """Changes persist across Config instances."""
        config1 = Config()
        config1.set("provider", "gemini")
        config1.save()

        config2 = Config()
        assert config2.get("provider") == "gemini"

    def test_merge_with_saved(self, config_dir):
        """Saved config merges with defaults (new defaults appear)."""
        config_path = config_dir / ".chatty-chronos" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"provider": "ollama"}))

        config = Config()
        assert config.get("provider") == "ollama"
        # Default fields should still be present
        assert config.get("model") == ""

    def test_set_bool_value(self, config_dir):
        config = Config()
        config.set("streaming", False)
        assert config.get("streaming") is False

    def test_set_int_value(self, config_dir):
        config = Config()
        config.set("local_server_port", 9090)
        assert config.get("local_server_port") == 9090

    def test_config_dir_created(self, config_dir):
        config = Config()
        assert config.dir.exists()

    def test_overwrite_existing_key(self, config_dir):
        config = Config()
        config.set("provider", "ollama")
        config.set("provider", "llamacpp")
        assert config.get("provider") == "llamacpp"

    def test_data_property(self, config_dir):
        """data property returns dict representation."""
        config = Config()
        data = config.data
        assert isinstance(data, dict)
        assert "provider" in data
        assert "model" in data

    def test_invalid_json_fallback(self, config_dir):
        """Corrupt config file falls back to defaults."""
        config_path = config_dir / "config.json"
        config_path.write_text("not valid json {{{")

        config = Config()
        assert config.get("provider") == "ollama"  # default

    def test_set_local_server_model(self, config_dir):
        config = Config()
        config.set("local_server_model", "E:\\models\\test.gguf")
        assert config.get("local_server_model") == "E:\\models\\test.gguf"

    def test_set_llamacpp_host(self, config_dir):
        config = Config()
        config.set("llamacpp_host", "http://localhost:9090")
        assert config.get("llamacpp_host") == "http://localhost:9090"
