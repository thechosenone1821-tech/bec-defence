"""Pytest guard for the active runtime import policy.

VIGIL's torch/torchvision/cv2 dependencies are allowed. Legacy live-action and
Commander/SLM client modules are not. Source-level imports of the legacy
containment planner are blocked by tools/check_no_live_executor.py; compatibility
tests may introspect that deterministic module object, so this runtime guard
checks the live-action bus/clients actually imported by the session.
"""
from __future__ import annotations

import sys

FORBIDDEN_MODULE_PREFIXES = (
    "spine.bus",
    "spine.slm_client",
    "spine.orchestrator",
    "ollama",
    "transformers",
    "tensorflow",
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
        raise RuntimeError(f"active runtime policy: forbidden modules loaded: {loaded}")


def pytest_sessionfinish(session, exitstatus):
    if _loaded_forbidden_modules():
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    loaded = _loaded_forbidden_modules()
    if loaded:
        terminalreporter.write_line(f"ACTIVE RUNTIME POLICY FAILED: forbidden modules loaded: {loaded}")
    else:
        terminalreporter.write_line("OK: active runtime imports no legacy live-action or Commander modules; VIGIL weights allowed")
