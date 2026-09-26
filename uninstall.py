#!/usr/bin/env python3
"""Chatty Chronos v3 — Uninstaller.

Usage:
    python uninstall.py             # Interactive uninstall
    python uninstall.py --all       # Remove everything including user data
    python uninstall.py --keep-data # Remove code but keep ~/.chatty-chronos
"""
import subprocess
import sys
import shutil
from pathlib import Path

INSTALL_DIR = Path(__file__).parent.resolve()
USER_DATA_DIR = Path.home() / ".chatty-chronos"


def ask_yes_no(prompt, default="y"):
    choice = input(f"  {prompt} [{'Y/n' if default == 'y' else 'y/N'}]: ").strip().lower()
    if not choice:
        return default == "y"
    return choice in ("y", "yes")


def uninstall_package():
    """Remove the pip package."""
    print("  Uninstalling pip package...")
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "chatty-chronos", "-y"],
        capture_output=True
    )
    print("[OK] Package uninstalled")


def remove_install_dir():
    """Remove the cloned repo / install directory."""
    if INSTALL_DIR.exists():
        print(f"  Removing: {INSTALL_DIR}")
        # We can't delete ourselves while running, so use a trick
        if sys.platform == "win32":
            # On Windows, schedule deletion after script exits
            bat = INSTALL_DIR / "_cleanup.bat"
            bat.write_text(
                f'@echo off\n'
                f'timeout /t 2 /nobreak >nul\n'
                f'rmdir /s /q "{INSTALL_DIR}"\n'
                f'del "%~f0"\n'
            )
            print(f"[OK] Install directory will be removed after exit")
            print(f"  (Run _cleanup.bat if it doesn't auto-delete)")
            return str(bat)
        else:
            print(f"  Run manually: rm -rf \"{INSTALL_DIR}\"")
    return None


def remove_user_data():
    """Remove ~/.chatty-chronos (config, memory, vectordb, etc)."""
    if USER_DATA_DIR.exists():
        print(f"  Removing user data: {USER_DATA_DIR}")
        shutil.rmtree(USER_DATA_DIR)
        print("[OK] User data removed")
    else:
        print("  No user data found.")


def main():
    args = sys.argv[1:]
    remove_all = "--all" in args
    keep_data = "--keep-data" in args

    print(f"\n{'='*50}")
    print(f"  Chatty Chronos v3 - Uninstaller")
    print(f"{'='*50}\n")
    print(f"  Install dir: {INSTALL_DIR}")
    print(f"  User data:   {USER_DATA_DIR}")
    print()

    if not remove_all and not keep_data:
        # Interactive mode
        if not ask_yes_no("Uninstall Chatty Chronos?"):
            print("  Cancelled.")
            return

    # Step 1: Uninstall pip package
    print("\n[1/3] Removing pip package...")
    uninstall_package()

    # Step 2: User data
    if remove_all:
        print("\n[2/3] Removing user data...")
        remove_user_data()
    elif keep_data:
        print("\n[2/3] Keeping user data (--keep-data)")
    else:
        print(f"\n[2/3] User data ({USER_DATA_DIR}):")
        print(f"  Contains: config, memory, vectordb, providers, session history")
        if ask_yes_no("Remove user data too?", default="n"):
            remove_user_data()
        else:
            print("  Kept user data.")

    # Step 3: Install directory
    print("\n[3/3] Removing install directory...")
    cleanup_bat = remove_install_dir()

    print(f"\n{'='*50}")
    print(f"  UNINSTALL COMPLETE")
    print(f"{'='*50}\n")

    if cleanup_bat and sys.platform == "win32":
        # Auto-run cleanup
        subprocess.Popen(f'cmd /c "{cleanup_bat}"', shell=True)


if __name__ == "__main__":
    main()
