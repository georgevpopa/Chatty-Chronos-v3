#!/usr/bin/env python3
"""Chatty Chronos v3 — Cross-platform auto-deploy script.

Usage:
    python deploy.py                 # Interactive install
    python deploy.py --skip-models   # Skip pulling Ollama models
    python deploy.py --update        # Update existing install
    python deploy.py --path "D:\\my\\path"  # Install to custom path
"""
import subprocess
import sys
import os
import platform
import shutil
from pathlib import Path

REPO_URL = "https://github.com/georgevpopa/Chatty-Chronos-v1.git"
MODELS = ["llama3.1:latest", "nomic-embed-text:latest"]


def run(cmd, check=True, capture=False):
    """Run a shell command."""
    print(f"  > {cmd}")
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture, text=True)


def ask(prompt, default=""):
    """Ask user for input with a default value."""
    if default:
        user_input = input(f"  {prompt} [{default}]: ").strip()
        return user_input or default
    return input(f"  {prompt}: ").strip()


def check_python():
    v = sys.version_info
    if v < (3, 10):
        print(f"[FAIL] Python 3.10+ required (you have {v.major}.{v.minor})")
        sys.exit(1)
    print(f"[OK] Python {v.major}.{v.minor}.{v.micro} found at {sys.executable}")


def check_git():
    if not shutil.which("git"):
        print("[FAIL] git not found. Install from: https://git-scm.com/download/win")
        sys.exit(1)
    print("[OK] git available")


def check_ollama():
    """Check if Ollama is installed. Support custom path."""
    ollama_path = shutil.which("ollama")
    if not ollama_path:
        print("[WARN] Ollama not found on PATH.")
        custom = ask("Enter Ollama executable path (or press Enter to skip)", "")
        if custom and Path(custom).exists():
            ollama_path = custom
        else:
            print("  Skipping Ollama setup. You can configure it later in /config.")
            return None

    # Check if running
    result = subprocess.run(f'"{ollama_path}" list', shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARN] Ollama not responding. Start it with: ollama serve")
        print(f"  Path: {ollama_path}")
        return ollama_path  # Return path but note it's not running

    print(f"[OK] Ollama running ({ollama_path})")
    return ollama_path


def choose_install_dir(args) -> Path:
    """Let user choose install directory."""
    # Check if --path was passed
    if "--path" in args:
        idx = args.index("--path")
        if idx + 1 < len(args):
            return Path(args[idx + 1])

    default_dir = str(Path.cwd() / "Chatty-Chronos-v1")
    print(f"\n  Where should Chatty Chronos be installed?")
    chosen = ask("Install path", default_dir)
    return Path(chosen)


def clone_repo(install_dir: Path):
    if install_dir.exists() and (install_dir / ".git").exists():
        print(f"  Directory exists, updating...")
        run(f'git -C "{install_dir}" pull')
    elif install_dir.exists():
        print(f"  Directory exists (not a git repo). Using as-is.")
    else:
        run(f'git clone {REPO_URL} "{install_dir}"')
    print(f"[OK] Repo ready at {install_dir}")


def install_package(install_dir: Path):
    run(f'"{sys.executable}" -m pip install -e "{install_dir}" --quiet')
    print("[OK] Package installed")


def pull_models(ollama_path: str):
    for model in MODELS:
        print(f"  Pulling {model}...")
        subprocess.run(f'"{ollama_path}" pull {model}', shell=True, check=False)
    print("[OK] Models ready")


def configure_ollama_host(install_dir: Path, ollama_path: str = None):
    """Ask user for Ollama host if using custom setup."""
    config_dir = Path.home() / ".chatty-chronos"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"

    import json
    config = {}
    if config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)

    print(f"\n  Ollama host configuration:")
    host = ask("Ollama API URL", config.get("ollama_host", "http://localhost:11434"))
    model = ask("Default model", config.get("model", "llama3.1:latest"))

    config["ollama_host"] = host
    config["model"] = model
    config["streaming"] = True
    config["max_context_messages"] = 20

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    print(f"[OK] Config saved to {config_file}")


def create_launcher(install_dir: Path):
    """Create start.bat / start.sh in the install directory."""
    if platform.system() == "Windows":
        launcher = install_dir / "start.bat"
        launcher.write_text(
            f'@echo off\ncd /d "{install_dir}"\npython main.py\npause\n'
        )
        print(f"[OK] Launcher: {launcher}")
        print(f"  Tip: Right-click start.bat > Create Shortcut, then move the shortcut anywhere.")
    else:
        launcher = install_dir / "start.sh"
        launcher.write_text(
            f'#!/bin/bash\ncd "{install_dir}"\npython3 main.py\n'
        )
        launcher.chmod(0o755)
        print(f"[OK] Launcher: {launcher}")


def main():
    args = sys.argv[1:]
    skip_models = "--skip-models" in args
    update_only = "--update" in args

    print(f"\n{'='*50}")
    print(f"  Chatty Chronos v3 - Auto Deploy")
    print(f"  OS: {platform.system()} ({platform.machine()})")
    print(f"{'='*50}\n")

    # Step 1: Prerequisites
    print("[1/6] Checking prerequisites...")
    check_python()
    check_git()
    ollama_path = check_ollama()

    # Step 2: Choose directory
    print("\n[2/6] Install location...")
    install_dir = choose_install_dir(args)

    # Step 3: Clone/Update
    print("\n[3/6] Getting source code...")
    clone_repo(install_dir)

    # Step 4: Install
    print("\n[4/6] Installing package...")
    install_package(install_dir)

    # Step 5: Configure + Models
    print("\n[5/6] Configuration...")
    configure_ollama_host(install_dir, ollama_path)
    if not skip_models and ollama_path:
        pull_opt = ask("Pull Ollama models? (llama3.1 + nomic-embed-text)", "y")
        if pull_opt.lower() in ("y", "yes"):
            pull_models(ollama_path)
    else:
        print("  Skipping model pull")

    # Step 6: Launcher
    print("\n[6/6] Creating launcher...")
    create_launcher(install_dir)

    # Done
    print(f"\n{'='*50}")
    print(f"  DEPLOYMENT COMPLETE")
    print(f"{'='*50}")
    print(f"\n  To start:")
    print(f"    cd \"{install_dir}\"")
    print(f"    python main.py")
    if platform.system() == "Windows":
        print(f"\n  Or double-click: {install_dir / 'start.bat'}")
        print(f"  (Create a shortcut to it for quick access from anywhere)")
    else:
        print(f"\n  Or run: {install_dir / 'start.sh'}")
    print()


if __name__ == "__main__":
    main()
