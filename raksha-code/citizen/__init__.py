"""RAKSHA Citizen compatibility alias for the modular layout.

`citizen.*` imports now resolve to `apps.citizen.*`. The authored provenance
Markdown files and PWA assets remain in this compatibility tree and are appended
to `apps.citizen.__path__`; no second Citizen service is created.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import apps.citizen as _impl
except ImportError as exc:  # pragma: no cover - defensive message only
    raise ImportError(
        "Phase 2 Citizen compatibility requires the repo root (or "
        "raksha-code/apps symlink) on sys.path"
    ) from exc

_LEGACY_DIR = str(Path(__file__).resolve().parent)
if _LEGACY_DIR not in _impl.__path__:
    _impl.__path__.append(_LEGACY_DIR)

sys.modules[__name__] = _impl
