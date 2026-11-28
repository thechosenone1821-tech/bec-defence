"""Shared test fixtures.

The FORTRESS tripwire is deliberately a process-wide singleton (organs, bus and
Governor must all feed the same 60-second window). Tests therefore need a
pristine window for each case, and the sanctioned way to open one again after a
freeze is the human step-up reset — exactly what a real human operator does.
"""

import os
import sys

import pytest

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(CODE_ROOT)
for _path in (REPO_ROOT, CODE_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)


@pytest.fixture(autouse=True)
def _fresh_tripwire():
    try:
        from spine import tripwire
        tripwire.shared().reset(human_stepup=True, note="test fixture: clean window")
    except Exception:
        pass
    yield
