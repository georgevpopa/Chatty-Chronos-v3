"""Tests for spec/generator.py — AI-assisted spec-driven development."""
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── slugify ──────────────────────────────────────────────────────────────────
class TestSlugify:
    def test_simple_name(self):
        from spec.generator import slugify
        assert slugify("Add Authentication") == "add-authentication"

    def test_with_special_chars(self):
        from spec.generator import slugify
        assert slugify("User's Profile! @Settings") == "users-profile-settings"

    def test_with_underscores(self):
        from spec.generator import slugify
        assert slugify("my_cool_feature") == "my-cool-feature"

    def test_multiple_spaces(self):
        from spec.generator import slugify
        assert slugify("hello   world") == "hello-world"

    def test_empty_string(self):
        from spec.generator import slugify
        assert slugify("") == ""

    def test_only_special_chars(self):
        from spec.generator import slugify
        assert slugify("!@#$%") == ""

    def test_mixed_case(self):
        from spec.generator import slugify
        assert slugify("My Feature Name") == "my-feature-name"


# ─── get_steering_context ────────────────────────────────────────────────────
class TestGetSteeringContext:
    def test_steering_exists(self, tmp_path, monkeypatch):
        """Returns content when STEERING.md exists."""
        (tmp_path / "STEERING.md").write_text("# Project Context\nUse type hints.")
        monkeypatch.chdir(tmp_path)

        from spec.generator import get_steering_context
        result = get_steering_context()

        assert "Project Context" in result
        assert "type hints" in result

    def test_steering_not_exists(self, tmp_path, monkeypatch):
        """Returns empty string when STEERING.md doesn't exist."""
        monkeypatch.chdir(tmp_path)

        from spec.generator import get_steering_context
        result = get_steering_context()

        assert result == ""


# ─── create_spec (templates only) ────────────────────────────────────────────
class TestCreateSpecTemplates:
    def test_creates_spec_dir(self, tmp_path, monkeypatch):
        """Creates a new spec directory with template files."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        from spec.generator import create_spec
        spec_dir, files = create_spec("Add Login", ai_generate=False)

        assert Path(spec_dir).exists()
        assert "requirements.md" in files
        assert "design.md" in files
        assert "tasks.md" in files

    def test_template_substitutes_feature_name(self, tmp_path, monkeypatch):
        """Template files have {feature_name} replaced."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        from spec.generator import create_spec
        spec_dir, _ = create_spec("User Authentication", ai_generate=False)

        req_content = (Path(spec_dir) / "requirements.md").read_text()
        assert "User Authentication" in req_content
        assert "{feature_name}" not in req_content

    def test_existing_spec_dir_not_overwritten(self, tmp_path, monkeypatch):
        """Existing spec dir is reused, not deleted."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        specs_dir = tmp_path / "specs" / "add-login"
        specs_dir.mkdir(parents=True)
        (specs_dir / "existing.md").write_text("existing content")

        from spec.generator import create_spec
        spec_dir, files = create_spec("Add Login", ai_generate=False)

        assert (Path(spec_dir) / "existing.md").exists()
        assert "requirements.md" in files

    def test_empty_feature_name(self, tmp_path, monkeypatch):
        """Empty feature name creates a slug with empty name."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        from spec.generator import create_spec
        spec_dir, files = create_spec("", ai_generate=False)

        assert Path(spec_dir).exists()
        assert len(files) == 3


# ─── create_spec (AI-generated) ──────────────────────────────────────────────
class TestCreateSpecAI:
    @patch("spec.generator._generate_phase")
    def test_ai_generate_creates_files(self, mock_gen, tmp_path, monkeypatch):
        """AI generation creates requirement, design, and tasks files."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        mock_gen.return_value = "AI generated content for this phase"

        from core.config import Config
        config = Config()

        from spec.generator import create_spec
        spec_dir, files = create_spec("Add JWT Auth", ai_generate=True, config=config)

        assert "requirements.md" in files
        assert "design.md" in files
        assert "tasks.md" in files
        assert mock_gen.call_count == 3

        # Check file contents
        req_content = (Path(spec_dir) / "requirements.md").read_text()
        assert "AI generated content" in req_content

    @patch("spec.generator._generate_phase")
    def test_ai_generate_passes_context(self, mock_gen, tmp_path, monkeypatch):
        """Each phase receives appropriate context from previous phases."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        mock_gen.side_effect = ["Requirements content", "Design content", "Tasks content"]

        from core.config import Config
        config = Config()

        from spec.generator import create_spec
        create_spec("Feature", ai_generate=True, config=config)

        # First call (requirements) gets steering context only
        call1_context = mock_gen.call_args_list[0][0][2]
        # Second call (design) gets steering + requirements
        call2_context = mock_gen.call_args_list[1][0][2]
        assert "Requirements content" in call2_context

    @patch("spec.generator._generate_phase")
    def test_ai_generate_without_config_skips(self, mock_gen, tmp_path, monkeypatch):
        """Without config, AI generation is skipped."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        from spec.generator import create_spec
        spec_dir, files = create_spec("Feature", ai_generate=True, config=None)

        # Should use templates instead
        assert mock_gen.call_count == 0
        assert len(files) == 3


# ─── _generate_phase ──────────────────────────────────────────────────────────
class TestGeneratePhase:
    @patch("llm.fallback.get_available_providers", return_value=[])
    @patch("spec.generator.ollama_provider.chat")
    def test_ollama_provider(self, mock_chat, mock_providers, tmp_path, monkeypatch):
        """Uses ollama provider when provider is 'ollama'."""
        monkeypatch.chdir(tmp_path)
        mock_response = MagicMock()
        mock_response.message.content = "Generated requirements"
        mock_chat.return_value = mock_response

        from core.config import Config
        config = Config()
        config.set("provider", "ollama")
        config.set("model", "test-model")

        from spec.generator import _generate_phase
        result = _generate_phase("Feature", "requirements", "", config)

        assert result == "Generated requirements"
        mock_chat.assert_called_once()

    @patch("llm.fallback.get_available_providers", return_value=[])
    @patch("llm.llamacpp_provider.chat")
    def test_llamacpp_provider(self, mock_chat, mock_providers, tmp_path, monkeypatch):
        """Uses llamacpp provider when provider is 'llamacpp'."""
        monkeypatch.chdir(tmp_path)
        mock_response = MagicMock()
        mock_response.message.content = "Generated via llama.cpp"
        mock_chat.return_value = mock_response

        from core.config import Config
        config = Config()
        config.set("provider", "llamacpp")
        config.set("model", "model.gguf")
        config.set("llamacpp_host", "http://localhost:8069")

        from spec.generator import _generate_phase
        result = _generate_phase("Feature", "design", "", config)

        assert result == "Generated via llama.cpp"
        mock_chat.assert_called_once()

    @patch("llm.fallback.get_available_providers")
    @patch("llm.openai_provider.chat")
    def test_cloud_provider(self, mock_chat, mock_providers, tmp_path, monkeypatch):
        """Uses openai_provider for cloud providers."""
        monkeypatch.chdir(tmp_path)
        mock_response = MagicMock()
        mock_response.message.content = "Generated via cloud"
        mock_chat.return_value = mock_response

        cloud_providers = [{"name": "nvidia", "type": "cloud", "base_url": "https://api.nvidia.com/v1", "env_key": "NVIDIA_API_KEY", "model": "nvidia/llama-3.1-nemotron-70b-instruct"}]
        mock_providers.return_value = cloud_providers

        from core.config import Config
        config = Config()
        config.set("provider", "nvidia")
        config.set("model", "nvidia/llama-3.1-nemotron-70b-instruct")

        from spec.generator import _generate_phase
        result = _generate_phase("Feature", "tasks", "", config)

        assert result == "Generated via cloud"
        mock_chat.assert_called_once()

    @patch("llm.fallback.get_available_providers", return_value=[])
    @patch("spec.generator.ollama_provider.chat")
    def test_empty_response(self, mock_chat, mock_providers, tmp_path, monkeypatch):
        """Empty response returns empty string."""
        monkeypatch.chdir(tmp_path)
        mock_response = MagicMock()
        mock_response.message.content = None
        mock_chat.return_value = mock_response

        from core.config import Config
        config = Config()
        config.set("provider", "ollama")

        from spec.generator import _generate_phase
        result = _generate_phase("Feature", "requirements", "", config)

        assert result == ""


# ─── list_specs ───────────────────────────────────────────────────────────────
class TestListSpecs:
    def test_no_specs_dir(self, tmp_path, monkeypatch):
        """Returns empty list when specs dir doesn't exist."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        from spec.generator import list_specs
        result = list_specs()

        assert result == []

    def test_list_with_specs(self, tmp_path, monkeypatch):
        """Lists existing specs with their files."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        # Create some specs
        (tmp_path / "specs" / "feature-a").mkdir(parents=True)
        (tmp_path / "specs" / "feature-a" / "requirements.md").write_text("req")
        (tmp_path / "specs" / "feature-a" / "design.md").write_text("design")

        (tmp_path / "specs" / "feature-b").mkdir(parents=True)
        (tmp_path / "specs" / "feature-b" / "tasks.md").write_text("tasks")

        from spec.generator import list_specs
        result = list_specs()

        assert len(result) == 2
        names = [s["name"] for s in result]
        assert "feature-a" in names
        assert "feature-b" in names

    def test_list_excludes_non_md_files(self, tmp_path, monkeypatch):
        """Only .md files are listed in spec."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        (tmp_path / "specs" / "feature").mkdir(parents=True)
        (tmp_path / "specs" / "feature" / "requirements.md").write_text("req")
        (tmp_path / "specs" / "feature" / "notes.txt").write_text("notes")
        (tmp_path / "specs" / "feature" / ".gitkeep").write_text("")

        from spec.generator import list_specs
        result = list_specs()

        assert len(result) == 1
        assert result[0]["files"] == ["requirements.md"]

    def test_list_sorted(self, tmp_path, monkeypatch):
        """Specs are listed in sorted order."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("spec.generator.SPECS_DIR", tmp_path / "specs")

        (tmp_path / "specs" / "z-feature").mkdir(parents=True)
        (tmp_path / "specs" / "a-feature").mkdir(parents=True)
        (tmp_path / "specs" / "m-feature").mkdir(parents=True)

        from spec.generator import list_specs
        result = list_specs()

        names = [s["name"] for s in result]
        assert names == ["a-feature", "m-feature", "z-feature"]
