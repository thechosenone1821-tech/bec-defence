"""Pytest guard for Phase 4's maintainer instruction: run no AI models.

The companion runner skips every test file that would import frozen
VoiceGuard/MAYA modules, an SLM/Commander client, the spine bus, or call the
old voice-scoring endpoint. This plugin additionally fails the session if any
forbidden module is present in ``sys.modules`` at finish.
"""
from __future__ import annotations

import sys

FORBIDDEN_MODULE_PREFIXES = (
    "citizen.voiceguard",
    "voiceguard",
    "maya",
    "run_maya",
    "spine.slm_client",
    "spine.orchestrator",
    "spine.bus",
)


def _loaded_forbidden_modules():
    return sorted(
        name for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".")
               for prefix in FORBIDDEN_MODULE_PREFIXES)
    )


def pytest_configure(config):
    loaded = _loaded_forbidden_modules()
    if loaded:
        raise RuntimeError(f"Phase 4 no-AI test policy: forbidden modules loaded: {loaded}")


def pytest_sessionfinish(session, exitstatus):
    loaded = _loaded_forbidden_modules()
    if loaded:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    loaded = _loaded_forbidden_modules()
    if loaded:
        terminalreporter.write_line(f"PHASE 4 NO-AI POLICY FAILED: forbidden modules loaded: {loaded}")
    else:
        terminalreporter.write_line("OK: no AI / VoiceGuard / MAYA / SLM model modules loaded during pytest.")
