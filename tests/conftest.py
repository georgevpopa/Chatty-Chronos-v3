"""Shared pytest fixtures.

Isolates the Chronos user directory (~/.chatty-chronos) into a temporary location
for the whole test session, so tests that call config.set(...) don't write to the
real user config or contaminate each other.
"""
import os
import tempfile
import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolate_chronos_home():
    """Point HOME/USERPROFILE at a temp dir for the test session."""
    tmp = tempfile.mkdtemp(prefix="chronos-test-home-")
    old_home = os.environ.get("HOME")
    old_userprofile = os.environ.get("USERPROFILE")
    os.environ["HOME"] = tmp
    os.environ["USERPROFILE"] = tmp
    try:
        yield tmp
    finally:
        if old_home is not None:
            os.environ["HOME"] = old_home
        else:
            os.environ.pop("HOME", None)
        if old_userprofile is not None:
            os.environ["USERPROFILE"] = old_userprofile
        else:
            os.environ.pop("USERPROFILE", None)
