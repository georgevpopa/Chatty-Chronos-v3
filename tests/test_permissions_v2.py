"""Tests for core/permissions.py — extended coverage for Web UI and ask_user flows."""
import threading
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import core.permissions as perms


# ─── Web UI permission flow ──────────────────────────────────────────────────
class TestWebUIPermission:
    def test_web_mode_y_approves(self):
        """Web mode with 'y' response approves permission."""
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        old_web = perms._web_mode_active
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            perms._web_mode_active = True

            mock_yield = MagicMock()
            perms.thread_local.yield_func = mock_yield

            # Simulate HTTP response setting response to "y"
            def fake_wait():
                with perms._pending_permissions_lock:
                    for req_id in perms._pending_permissions:
                        perms._pending_permissions[req_id]["response"] = "y"
                        perms._pending_permissions[req_id]["event"].set()

            # Patch event.wait to simulate immediate response
            with patch("threading.Event") as mock_event:
                mock_event.return_value.wait = fake_wait
                result = perms.request_permission("test_tool", "test desc")

            assert result is True
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust
            perms._web_mode_active = old_web
            perms.thread_local.yield_func = None
            perms._pending_permissions.clear()

    def test_web_mode_ya_sets_session_trust(self):
        """Web mode with 'ya' response sets session trust."""
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        old_web = perms._web_mode_active
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            perms._web_mode_active = True

            mock_yield = MagicMock()
            perms.thread_local.yield_func = mock_yield

            def fake_wait():
                with perms._pending_permissions_lock:
                    for req_id in perms._pending_permissions:
                        perms._pending_permissions[req_id]["response"] = "ya"
                        perms._pending_permissions[req_id]["event"].set()

            with patch("threading.Event") as mock_event:
                mock_event.return_value.wait = fake_wait
                result = perms.request_permission("test_tool", "test desc")

            assert result is True
            assert perms._session_trust_all is True
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust
            perms._web_mode_active = old_web
            perms.thread_local.yield_func = None
            perms._pending_permissions.clear()

    def test_web_mode_deny(self):
        """Web mode with 'n' response denies permission."""
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        old_web = perms._web_mode_active
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            perms._web_mode_active = True

            mock_yield = MagicMock()
            perms.thread_local.yield_func = mock_yield

            def fake_wait():
                with perms._pending_permissions_lock:
                    for req_id in perms._pending_permissions:
                        perms._pending_permissions[req_id]["response"] = "n"
                        perms._pending_permissions[req_id]["event"].set()

            with patch("threading.Event") as mock_event:
                mock_event.return_value.wait = fake_wait
                result = perms.request_permission("test_tool", "test desc")

            assert result is False
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust
            perms._web_mode_active = old_web
            perms.thread_local.yield_func = None
            perms._pending_permissions.clear()

    def test_web_mode_yield_error(self):
        """When yield_func raises, returns False."""
        old_auto = perms._auto_approve_override
        old_trust = perms._session_trust_all
        old_web = perms._web_mode_active
        try:
            perms._auto_approve_override = False
            perms._session_trust_all = False
            perms._web_mode_active = True

            mock_yield = MagicMock(side_effect=Exception("SSE error"))
            perms.thread_local.yield_func = mock_yield

            result = perms.request_permission("test_tool", "test desc")
            assert result is False
        finally:
            perms._auto_approve_override = old_auto
            perms._session_trust_all = old_trust
            perms._web_mode_active = old_web
            perms.thread_local.yield_func = None


# ─── ask_user_prompt Web UI flow ──────────────────────────────────────────────
class TestAskUserPromptWebUI:
    def test_web_mode_returns_response(self):
        old_web = perms._web_mode_active
        try:
            perms._web_mode_active = True
            mock_yield = MagicMock()
            perms.thread_local.yield_func = mock_yield

            def fake_wait():
                with perms._pending_prompts_lock:
                    for req_id in perms._pending_prompts:
                        perms._pending_prompts[req_id]["response"] = "dark theme"
                        perms._pending_prompts[req_id]["event"].set()

            with patch("threading.Event") as mock_event:
                mock_event.return_value.wait = fake_wait
                result = perms.ask_user_prompt("What theme?")

            assert result == "dark theme"
        finally:
            perms._web_mode_active = old_web
            perms.thread_local.yield_func = None
            perms._pending_prompts.clear()

    def test_web_mode_yield_error(self):
        old_web = perms._web_mode_active
        try:
            perms._web_mode_active = True
            mock_yield = MagicMock(side_effect=Exception("SSE error"))
            perms.thread_local.yield_func = mock_yield

            result = perms.ask_user_prompt("Question?")
            assert "No response" in result or result == ""
        finally:
            perms._web_mode_active = old_web
            perms.thread_local.yield_func = None
