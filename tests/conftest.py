"""Gemeinsame Test-Einstellungen: Offscreen-Qt, eigener Benutzerordner."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_USER = tempfile.mkdtemp(prefix="cfs-qt-test-")
os.environ["CFS_USER_DIR"] = _USER
os.environ["LANG"] = "de_DE.UTF-8"

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def user_dir():
    return _USER


@pytest.fixture(scope="session")
def engine():
    from cfs_core.engine import Engine
    return Engine()
