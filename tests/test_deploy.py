"""Tests for deploy.py — cross-platform auto-deploy script."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestRun:
    def test_run_success(self):
        from deploy import run
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            run("echo hello")

    def test_run_no_check(self):
        from deploy import run
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            run("false", check=False)


class TestAsk:
    def test_ask_with_default(self):
        from deploy import ask
        with patch("builtins.input", return_value=""):
            assert ask("Name", "default_val") == "default_val"

    def test_ask_user_input(self):
        from deploy import ask
        with patch("builtins.input", return_value="custom"):
            assert ask("Name", "default_val") == "custom"

    def test_ask_no_default(self):
        from deploy import ask
        with patch("builtins.input", return_value="answer"):
            assert ask("Question") == "answer"


class TestCheckPython:
    def test_check_python_ok(self):
        from deploy import check_python
        check_python()

    def test_check_python_old(self):
        from deploy import check_python
        mock_version = MagicMock()
        mock_version.__lt__ = lambda self, other: (3, 5, 0) < other
        mock_version.major = 3
        mock_version.minor = 5
        mock_version.micro = 0
        with patch("deploy.sys") as mock_sys:
            mock_sys.version_info = mock_version
            mock_sys.exit = MagicMock(side_effect=SystemExit(1))
            mock_sys.executable = "/usr/bin/python3"
            with pytest.raises(SystemExit):
                check_python()


class TestCheckGit:
    def test_check_git_ok(self):
        from deploy import check_git
        with patch("shutil.which", return_value="/usr/bin/git"):
            check_git()

    def test_check_git_missing(self):
        from deploy import check_git
        with patch("shutil.which", return_value=None), \
             patch("sys.exit") as mock_exit:
            check_git()
            mock_exit.assert_called_with(1)


class TestCheckOllama:
    def test_ollama_found(self):
        from deploy import check_ollama
        with patch("shutil.which", return_value="/usr/bin/ollama"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            assert check_ollama() == "/usr/bin/ollama"

    def test_ollama_not_found_skip(self):
        from deploy import check_ollama
        with patch("shutil.which", return_value=None), \
             patch("builtins.input", return_value=""):
            assert check_ollama() is None

    def test_ollama_not_found_custom_path(self, tmp_path):
        from deploy import check_ollama
        fake = tmp_path / "ollama.exe"
        fake.write_text("fake")
        with patch("shutil.which", return_value=None), \
             patch("builtins.input", return_value=str(fake)):
            assert check_ollama() == str(fake)

    def test_ollama_not_running(self):
        from deploy import check_ollama
        with patch("shutil.which", return_value="/usr/bin/ollama"), \
             patch("subprocess.run", return_value=MagicMock(returncode=1)):
            assert check_ollama() == "/usr/bin/ollama"


class TestChooseInstallDir:
    def test_with_path_arg(self):
        from deploy import choose_install_dir
        assert choose_install_dir(["--path", "/custom/path"]) == Path("/custom/path")

    def test_interactive(self):
        from deploy import choose_install_dir
        with patch("builtins.input", return_value="/my/path"):
            assert choose_install_dir([]) == Path("/my/path")


class TestCloneRepo:
    def test_existing_git_repo(self, tmp_path):
        from deploy import clone_repo
        (tmp_path / ".git").mkdir()
        with patch("deploy.run"):
            clone_repo(tmp_path)

    def test_existing_not_git(self, tmp_path):
        from deploy import clone_repo
        with patch("deploy.run"):
            clone_repo(tmp_path)

    def test_new_clone(self, tmp_path):
        from deploy import clone_repo
        with patch("deploy.run"):
            clone_repo(tmp_path / "new_repo")


class TestInstallPackage:
    def test_install(self, tmp_path):
        from deploy import install_package
        with patch("deploy.run"):
            install_package(tmp_path)


class TestPullModels:
    def test_pull(self):
        from deploy import pull_models
        with patch("subprocess.run"):
            pull_models("/usr/bin/ollama")


class TestConfigureOllamaHost:
    def test_configure(self, tmp_path):
        from deploy import configure_ollama_host
        with patch("pathlib.Path.home", return_value=tmp_path), \
             patch("builtins.input", side_effect=["http://localhost:11434", "llama3.1"]):
            configure_ollama_host(tmp_path)
            assert (tmp_path / ".chatty-chronos" / "config.json").exists()


class TestCreateLauncher:
    def test_windows(self, tmp_path):
        from deploy import create_launcher
        with patch("platform.system", return_value="Windows"):
            create_launcher(tmp_path)
            assert (tmp_path / "start.bat").exists()

    def test_linux(self, tmp_path):
        from deploy import create_launcher
        with patch("platform.system", return_value="Linux"):
            create_launcher(tmp_path)
            assert (tmp_path / "start.sh").exists()


class TestMain:
    def test_main_skip_models(self, tmp_path):
        from deploy import main
        with patch("sys.argv", ["deploy.py", "--skip-models", "--path", str(tmp_path)]), \
             patch("deploy.check_python"), patch("deploy.check_git"), \
             patch("deploy.check_ollama", return_value=None), \
             patch("deploy.clone_repo"), patch("deploy.install_package"), \
             patch("deploy.configure_ollama_host"), patch("deploy.create_launcher"):
            main()

    def test_main_update(self, tmp_path):
        from deploy import main
        with patch("sys.argv", ["deploy.py", "--update", "--path", str(tmp_path)]), \
             patch("deploy.check_python"), patch("deploy.check_git"), \
             patch("deploy.check_ollama", return_value="/usr/bin/ollama"), \
             patch("deploy.clone_repo"), patch("deploy.install_package"), \
             patch("deploy.configure_ollama_host"), patch("deploy.create_launcher"), \
             patch("deploy.ask", return_value="n"):
            main()
