"""Tests for core/permissions.py — 3-tier permission system."""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ─── Simple setters/getters ──────────────────────────────────────────────────
class TestSimpleSetters:
    def test_set_web_mode_active(self):
        import core.permissions as perms
        old = perms._web_mode_active
        try:
            perms.set_web_mode_active(True)
            assert perms._web_mode_active is True
            perms.set_web_mode_active(False)
            assert perms._web_mode_active is False
        finally:
            perms._web_mode_active = old

    def test_set_auto_approve_override(self):
        import core.permissions as perms
        old = perms._auto_approve_override
        try:
            perms.set_auto_approve_override(True)
            assert perms.get_auto_approve_override() is True
            perms.set_auto_approve_override(False)
            assert perms.get_auto_approve_override() is False
        finally:
            perms._auto_approve_override = old

    def test_reset_session_trust(self):
        import core.permissions as perms
        old = perms._session_trust_all
        try:
            perms._session_trust_all = True
            perms.reset_session_trust()
            assert perms._session_trust_all is False
        finally:
            perms._session_trust_all = old


# ─── Workspace trust ─────────────────────────────────────────────────────────
class TestWorkspaceTrust:
    def test_load_trusted_empty(self, tmp_path):
        import core.permissions as perms
        old = perms.TRUST_FILE
        try:
            perms.TRUST_FILE = tmp_path / "nonexistent"
            result = perms._load_trusted_workspaces()
            assert result == set()
        finally:
            perms.TRUST_FILE = old

    def test_save_and_load_trusted(self, tmp_path):
        import core.permissions as perms
        old = perms.TRUST_FILE
        try:
            trust_file = tmp_path / "trusted"
            perms.TRUST_FILE = trust_file
            perms._save_trusted_workspace("/my/workspace")
            loaded = perms._load_trusted_workspaces()
            assert "/my/workspace" in loaded
        finally:
            perms.TRUST_FILE = old

    def test_is_workspace_trusted_true(self, tmp_path):
        import core.permissions as perms
        old = perms.TRUST_FILE
        try:
            trust_file = tmp_path / "trusted"
            perms.TRUST_FILE = trust_file
            perms._save_trusted_workspace(str(tmp_path))
            assert perms.is_workspace_trusted(str(tmp_path)) is True
        finally:
            perms.TRUST_FILE = old

    def test_is_workspace_trusted_child(self, tmp_path):
        import core.permissions as perms
        old = perms.TRUST_FILE
        try:
            trust_file = tmp_path / "trusted"
            perms.TRUST_FILE = trust_file
            child = tmp_path / "child" / "nested"
            child.mkdir(parents=True)
            perms._save_trusted_workspace(str(tmp_path))
            assert perms.is_workspace_trusted(str(child)) is True
        finally:
            perms.TRUST_FILE = old

    def test_is_workspace_trusted_false(self, tmp_path):
        import core.permissions as perms
        old = perms.TRUST_FILE
        try:
            trust_file = tmp_path / "trusted"
            perms.TRUST_FILE = trust_file
            # Don't trust anything
            assert perms.is_workspace_trusted(str(tmp_path)) is False
        finally:
            perms.TRUST_FILE = old


# ─── request_permission ──────────────────────────────────────────────────────
class TestRequestPermission:
    def test_auto_approve_override(self):
        import core.permissions as perms
        old_auto = perms._auto_approve_override
        try:
            perms._auto_approve_override = True
            result = perms.request_permission("test_tool", "test desc")
            assert result is True
        finally:
            perms._auto_approve_override = old_auto

    def test_session_trust_all(self):
        import core.permissions as perms
        old_trust = perms._session_trust_all
        try:
            perms._session_trust_all = True
            result = perms.request_permission("test_tool", "test desc")
            assert result is True
        finally:
            perms._session_trust_all = old_trust

    def test_workspace_trusted(self, tmp_path):
        import core.permissions as perms
        old_trust = perms.TRUST_FILE
        try:
            trust_file = tmp_path / "trusted"
            perms.TRUST_FILE = trust_file
            perms._save_trusted_workspace(str(tmp_path))
            result = perms.request_permission("test_tool", "test desc", cwd=str(tmp_path))
            assert result is True
        finally:
            perms.TRUST_FILE = old_trust

    def test_auto_approve_from_config(self, tmp_path):
        import core.permissions as perms
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            # Mock Config to return auto_approve_tools=True
            with patch("core.config.Config") as MockConfig:
                mock_cfg = MagicMock()
                mock_cfg.get.return_value = True
                MockConfig.return_value = mock_cfg
                result = perms.request_permission("test_tool", "test desc")
                assert result is True
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust

    def test_deny_returns_false(self):
        import core.permissions as perms
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            with patch("questionary.select", side_effect=ImportError("no console")), \
                 patch("builtins.input", return_value="n"):
                result = perms.request_permission("test_tool", "test desc")
                assert result is False
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust

    def test_allow_once(self):
        import core.permissions as perms
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            with patch("questionary.select", side_effect=ImportError("no console")), \
                 patch("builtins.input", return_value="y"):
                result = perms.request_permission("test_tool", "test desc")
                assert result is True
                assert perms._session_trust_all is False
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust

    def test_yes_all_sets_session_trust(self):
        import core.permissions as perms
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            with patch("questionary.select", side_effect=ImportError("no console")), \
                 patch("builtins.input", return_value="ya"):
                result = perms.request_permission("test_tool", "test desc")
                assert result is True
                assert perms._session_trust_all is True
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust

    def test_trust_workspace(self, tmp_path):
        import core.permissions as perms
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        old_trust_file = perms.TRUST_FILE
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            perms.TRUST_FILE = tmp_path / "trusted"
            with patch("questionary.select", side_effect=ImportError("no console")), \
                 patch("builtins.input", return_value="yw"):
                result = perms.request_permission("test_tool", "test desc", cwd=str(tmp_path))
                assert result is True
                loaded = perms._load_trusted_workspaces()
                assert str(tmp_path) in loaded
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust
            perms.TRUST_FILE = old_trust_file


# ─── ask_user_prompt ──────────────────────────────────────────────────────────
class TestAskUserPrompt:
    def test_cli_input(self):
        import core.permissions as perms
        old_web = perms._web_mode_active
        try:
            perms._web_mode_active = False
            with patch("questionary.text", side_effect=ImportError("no console")), \
                 patch("builtins.input", return_value="dark theme"):
                result = perms.ask_user_prompt("What theme?")
                assert result == "dark theme"
        finally:
            perms._web_mode_active = old_web

    def test_empty_input(self):
        import core.permissions as perms
        old_web = perms._web_mode_active
        try:
            perms._web_mode_active = False
            with patch("questionary.text", side_effect=ImportError("no console")), \
                 patch("builtins.input", return_value=""):
                result = perms.ask_user_prompt("Question?")
                assert result == ""
        finally:
            perms._web_mode_active = old_web

    def test_keyboard_interrupt(self):
        import core.permissions as perms
        old_web = perms._web_mode_active
        try:
            perms._web_mode_active = False
            with patch("questionary.text", side_effect=ImportError("no console")), \
                 patch("builtins.input", side_effect=KeyboardInterrupt):
                result = perms.ask_user_prompt("Question?")
                assert result == ""
        finally:
            perms._web_mode_active = old_web
