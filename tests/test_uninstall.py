"""Tests for uninstall.py — uninstall script."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestAskYesNo:
    def test_default_yes(self):
        from uninstall import ask_yes_no
        with patch("builtins.input", return_value=""):
            assert ask_yes_no("OK?") is True

    def test_default_no(self):
        from uninstall import ask_yes_no
        with patch("builtins.input", return_value=""):
            assert ask_yes_no("OK?", default="n") is False

    def test_user_says_yes(self):
        from uninstall import ask_yes_no
        with patch("builtins.input", return_value="yes"):
            assert ask_yes_no("OK?") is True

    def test_user_says_no(self):
        from uninstall import ask_yes_no
        with patch("builtins.input", return_value="no"):
            assert ask_yes_no("OK?") is False


class TestUninstallPackage:
    def test_uninstall(self):
        from uninstall import uninstall_package
        with patch("subprocess.run"):
            uninstall_package()


class TestRemoveInstallDir:
    def test_exists_win32(self, tmp_path):
        import uninstall
        with patch.object(uninstall, "INSTALL_DIR", tmp_path), \
             patch("sys.platform", "win32"):
            result = uninstall.remove_install_dir()
            assert result is not None

    def test_exists_linux(self, tmp_path):
        import uninstall
        with patch.object(uninstall, "INSTALL_DIR", tmp_path), \
             patch("sys.platform", "linux"):
            result = uninstall.remove_install_dir()
            assert result is None

    def test_not_exists(self, tmp_path):
        import uninstall
        fake = tmp_path / "nonexistent"
        with patch.object(uninstall, "INSTALL_DIR", fake):
            result = uninstall.remove_install_dir()
            assert result is None


class TestRemoveUserData:
    def test_exists(self, tmp_path):
        import uninstall
        (tmp_path / "data").mkdir()
        with patch.object(uninstall, "USER_DATA_DIR", tmp_path / "data"):
            uninstall.remove_user_data()

    def test_not_exists(self, tmp_path):
        import uninstall
        with patch.object(uninstall, "USER_DATA_DIR", tmp_path / "nonexistent"):
            uninstall.remove_user_data()


class TestMain:
    def test_main_all(self):
        import uninstall
        with patch("sys.argv", ["uninstall.py", "--all"]), \
             patch.object(uninstall, "uninstall_package"), \
             patch.object(uninstall, "remove_user_data"), \
             patch.object(uninstall, "remove_install_dir", return_value=None):
            uninstall.main()

    def test_main_keep_data(self):
        import uninstall
        with patch("sys.argv", ["uninstall.py", "--keep-data"]), \
             patch.object(uninstall, "uninstall_package"), \
             patch.object(uninstall, "remove_install_dir", return_value=None):
            uninstall.main()

    def test_main_interactive_confirm(self):
        import uninstall
        with patch("sys.argv", ["uninstall.py"]), \
             patch("builtins.input", return_value="y"), \
             patch.object(uninstall, "uninstall_package"), \
             patch.object(uninstall, "remove_user_data"), \
             patch.object(uninstall, "remove_install_dir", return_value=None):
            uninstall.main()

    def test_main_interactive_cancel(self):
        import uninstall
        with patch("sys.argv", ["uninstall.py"]), \
             patch("builtins.input", return_value="n"):
            uninstall.main()

    def test_main_interactive_keep_data(self):
        import uninstall
        with patch("sys.argv", ["uninstall.py"]), \
             patch("builtins.input", side_effect=["y", "n"]), \
             patch.object(uninstall, "uninstall_package"), \
             patch.object(uninstall, "remove_install_dir", return_value=None):
            uninstall.main()

    def test_main_interactive_remove_data(self):
        import uninstall
        with patch("sys.argv", ["uninstall.py"]), \
             patch("builtins.input", side_effect=["y", "y"]), \
             patch.object(uninstall, "uninstall_package"), \
             patch.object(uninstall, "remove_user_data"), \
             patch.object(uninstall, "remove_install_dir", return_value=None):
            uninstall.main()
