"""Tests for llm/fallback.py — multi-provider LLM fallback system."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── _load_providers ──────────────────────────────────────────────────────────
class TestLoadProviders:
    def test_creates_default_file(self, tmp_path):
        """Creates providers.json with defaults when file doesn't exist."""
        from llm.fallback import _load_providers, PROVIDERS_FILE

        with patch("llm.fallback.PROVIDERS_FILE", tmp_path / "providers.json"):
            providers = _load_providers()

        assert len(providers) > 0
        names = [p["name"] for p in providers]
        assert "ollama" in names
        assert "nvidia" in names

    def test_loads_existing_file(self, tmp_path):
        """Loads from existing providers.json with all defaults present."""
        from llm.fallback import DEFAULT_PROVIDERS
        providers_file = tmp_path / "providers.json"
        providers_file.write_text(json.dumps(DEFAULT_PROVIDERS))

        from llm.fallback import _load_providers

        with patch("llm.fallback.PROVIDERS_FILE", providers_file):
            providers = _load_providers()

        assert len(providers) == len(DEFAULT_PROVIDERS)
        names = [p["name"] for p in providers]
        assert "ollama" in names
        assert "nvidia" in names

    def test_missing_default_triggers_rewrite(self, tmp_path):
        """When a default provider is missing, file is rewritten with defaults."""
        partial = [{"name": "ollama", "type": "ollama", "is_local": True}]
        providers_file = tmp_path / "providers.json"
        providers_file.write_text(json.dumps(partial))

        from llm.fallback import _load_providers, DEFAULT_PROVIDERS

        with patch("llm.fallback.PROVIDERS_FILE", providers_file):
            providers = _load_providers()

        # Should have all defaults
        default_names = {p["name"] for p in DEFAULT_PROVIDERS}
        loaded_names = {p["name"] for p in providers}
        assert default_names.issubset(loaded_names)


# ─── _reload_env ──────────────────────────────────────────────────────────────
class TestReloadEnv:
    def test_calls_load_dotenv(self):
        """_reload_env calls load_dotenv for both paths."""
        from llm.fallback import _reload_env

        with patch("llm.fallback.load_dotenv") as mock_load:
            _reload_env()
            assert mock_load.call_count == 2


# ─── get_available_providers ──────────────────────────────────────────────────
class TestGetAvailableProviders:
    def test_local_provider_status(self, tmp_path):
        """Local providers get 'local' status."""
        from llm.fallback import get_available_providers

        providers = [{"name": "ollama", "type": "ollama", "is_local": True}]
        with patch("llm.fallback._load_providers", return_value=providers), \
             patch("llm.fallback._reload_env"):
            result = get_available_providers()

        assert len(result) == 1
        assert result[0]["status"] == "local"

    def test_configured_provider_status(self, tmp_path):
        """Providers with env_key and matching env var get 'configured' status."""
        from llm.fallback import get_available_providers

        providers = [{"name": "groq", "env_key": "GROQ_API_KEY", "model": "test"}]
        with patch("llm.fallback._load_providers", return_value=providers), \
             patch("llm.fallback._reload_env"), \
             patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            result = get_available_providers()

        assert len(result) == 1
        assert result[0]["status"] == "configured"

    def test_no_key_provider_status(self, tmp_path):
        """Providers without matching env key get 'no_key' status."""
        from llm.fallback import get_available_providers

        providers = [{"name": "groq", "env_key": "GROQ_API_KEY"}]
        with patch("llm.fallback._load_providers", return_value=providers), \
             patch("llm.fallback._reload_env"), \
             patch.dict(os.environ, {}, clear=True):
            result = get_available_providers()

        assert len(result) == 1
        assert result[0]["status"] == "no_key"


# ─── list_nvidia_models ───────────────────────────────────────────────────────
class TestListNvidiaModels:
    def test_no_api_key_returns_empty(self):
        """Returns empty when NVIDIA_API_KEY is not set."""
        from llm.fallback import list_nvidia_models

        with patch.dict(os.environ, {}, clear=True), \
             patch("llm.fallback._reload_env"):
            result = list_nvidia_models()

        assert result == []

    @patch("llm.fallback.httpx.Client")
    def test_successful_fetch(self, mock_client_cls):
        """Fetches models when API key is present."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "model-a"}, {"id": "model-b"}]
        }
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.fallback import list_nvidia_models

        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}):
            result = list_nvidia_models()

        assert result == ["model-a", "model-b"]

    @patch("llm.fallback.httpx.Client")
    def test_empty_response(self, mock_client_cls):
        """Returns empty when API returns no data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.fallback import list_nvidia_models

        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}):
            result = list_nvidia_models()

        assert result == []

    @patch("llm.fallback.httpx.Client")
    def test_exception_returns_empty(self, mock_client_cls):
        """Returns empty on HTTP error."""
        mock_client_cls.side_effect = Exception("Network error")

        from llm.fallback import list_nvidia_models

        with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}):
            result = list_nvidia_models()

        assert result == []


# ─── call_cloud_provider ──────────────────────────────────────────────────────
class TestCallCloudProvider:
    @patch("llm.fallback.httpx.Client")
    def test_successful_call(self, mock_client_cls):
        """Successful cloud provider call returns content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Cloud response"}}]
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.fallback import call_cloud_provider

        provider = {"name": "groq", "base_url": "https://api.groq.com/v1", "model": "test", "env_key": "GROQ_API_KEY"}
        messages = [{"role": "user", "content": "Hello"}]

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            result = call_cloud_provider(messages, provider)

        assert result == "Cloud response"

    def test_missing_api_key(self):
        """Raises ValueError when API key is missing."""
        from llm.fallback import call_cloud_provider

        provider = {"name": "groq", "env_key": "GROQ_API_KEY"}

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No API key"):
                call_cloud_provider([], provider)

    @patch("llm.fallback.httpx.Client")
    def test_rate_limit_error(self, mock_client_cls):
        """Raises RateLimitError on 429 status."""
        from llm.fallback import RateLimitError

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from llm.fallback import call_cloud_provider

        provider = {"name": "groq", "base_url": "https://api.groq.com/v1", "model": "test", "env_key": "GROQ_API_KEY"}

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            with pytest.raises(RateLimitError):
                call_cloud_provider([{"role": "user", "content": "test"}], provider)


# ─── chat_with_fallback ───────────────────────────────────────────────────────
class TestChatWithFallback:
    @patch("llm.ollama_provider.chat")
    def test_ollama_provider_works(self, mock_chat):
        """First provider (ollama) succeeds."""
        from llm.fallback import chat_with_fallback

        mock_response = MagicMock()
        mock_response.message.content = "Ollama response"
        mock_chat.return_value = mock_response

        providers = [{"name": "ollama", "type": "ollama", "is_local": True, "status": "local"}]

        with patch("llm.fallback.get_available_providers", return_value=providers), \
             patch("llm.fallback._reload_env"):
            from core.config import Config
            config = Config()
            result = chat_with_fallback([{"role": "user", "content": "test"}], config)

        assert result == "Ollama response"

    @patch("llm.fallback.call_cloud_provider")
    def test_cloud_provider_works(self, mock_cloud):
        """Cloud provider succeeds when configured."""
        from llm.fallback import chat_with_fallback

        mock_cloud.return_value = "Cloud response"

        providers = [{"name": "groq", "type": "openai_compatible", "status": "configured", "base_url": "https://api.groq.com/v1", "model": "test", "env_key": "GROQ_API_KEY"}]

        with patch("llm.fallback.get_available_providers", return_value=providers), \
             patch("llm.fallback._reload_env"):
            from core.config import Config
            config = Config()
            result = chat_with_fallback([{"role": "user", "content": "test"}], config)

        assert result == "Cloud response"

    @patch("llm.fallback.call_cloud_provider")
    def test_fallback_on_rate_limit(self, mock_cloud):
        """Falls back to next provider on rate limit."""
        from llm.fallback import chat_with_fallback, RateLimitError

        mock_cloud.side_effect = [
            RateLimitError("rate limited"),
            "Second provider response"
        ]

        providers = [
            {"name": "groq", "type": "openai_compatible", "status": "configured", "base_url": "url1", "model": "m1", "env_key": "K1"},
            {"name": "gemini", "type": "openai_compatible", "status": "configured", "base_url": "url2", "model": "m2", "env_key": "K2"},
        ]

        with patch("llm.fallback.get_available_providers", return_value=providers), \
             patch("llm.fallback._reload_env"), \
             patch.dict(os.environ, {"K1": "key1", "K2": "key2"}):
            from core.config import Config
            config = Config()
            result = chat_with_fallback([{"role": "user", "content": "test"}], config)

        assert result == "Second provider response"

    @patch("llm.fallback.call_cloud_provider")
    def test_all_providers_fail(self, mock_cloud):
        """Raises RuntimeError when all providers fail."""
        from llm.fallback import chat_with_fallback

        mock_cloud.side_effect = Exception("Connection failed")

        providers = [
            {"name": "groq", "type": "openai_compatible", "status": "configured", "base_url": "url1", "model": "m1", "env_key": "K1"},
        ]

        with patch("llm.fallback.get_available_providers", return_value=providers), \
             patch("llm.fallback._reload_env"):
            from core.config import Config
            config = Config()
            with pytest.raises(RuntimeError, match="All providers failed"):
                chat_with_fallback([{"role": "user", "content": "test"}], config)


# ─── RateLimitError ───────────────────────────────────────────────────────────
class TestRateLimitError:
    def test_is_exception(self):
        from llm.fallback import RateLimitError
        assert issubclass(RateLimitError, Exception)

    def test_can_be_caught(self):
        from llm.fallback import RateLimitError
        with pytest.raises(RateLimitError):
            raise RateLimitError("test")
