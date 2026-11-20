"""Shared test fixtures.

The FORTRESS tripwire is deliberately a process-wide singleton (organs, bus and
Governor must all feed the same 60-second window). Tests therefore need a
pristine window for each case, and the sanctioned way to open one again after a
freeze is the human step-up reset — exactly what a real human operator does.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _fresh_tripwire():
    try:
        from spine import tripwire
        tripwire.shared().reset(human_stepup=True, note="test fixture: clean window")
    except Exception:
        pass
    yield
