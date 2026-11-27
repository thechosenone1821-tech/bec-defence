"""Compatibility facade for the Phase 6–8 unified runtime.

The legacy ``spine.bus`` implementation is no longer imported. Callers that
used this path must supply the one active detector contract; the Infra app does
so through ``apps.infra.backend.app.create_app``.
"""
from __future__ import annotations

from typing import Any

from .runtime import create_app as _create_runtime_app


def create_app(*args: Any, **kwargs: Any):
    if "detector" not in kwargs:
        raise RuntimeError(
            "one active detector contract is required; use apps.infra.backend.app.create_app"
        )
    return _create_runtime_app(*args, **kwargs)


__all__ = ["create_app"]
