"""Machine-readable app-separation and no-bypass contract.

Two apps share one `packages/` layer. The Citizen app owns the VIGIL
model-backed image-privacy capability; Infra stays deterministic and read-only.
A live executor, legacy Commander/SLM client or legacy spine bus is never an
active import surface.
"""
from __future__ import annotations

APP_NAMES = ("citizen", "infra")
VIGIL_RUNTIME_ROOT = "packages/vigil"

FORBIDDEN_CROSS_APP_ROOTS = {
    "citizen": ("apps.infra", "apps.infra.backend", "apps.infra.detectors", "sentinel", "raavan", "corpora", "evals", "spine"),
    "infra": ("apps.citizen", "apps.citizen.api", "apps.citizen.messageguard", "apps.citizen.risk", "citizen", "spine"),
}

FORBIDDEN_APP_BYPASS_ROOTS = (
    "spine.bus", "spine.governor", "spine.ledger", "spine.containment",
    "spine.sanitizer", "spine.entity_graph", "spine.orchestrator",
    "sentinel.shields.base_organ.handle_rpc",
)

FORBIDDEN_LIVE_EXECUTOR_ROOTS = (
    "spine.slm_client", "spine.orchestrator", "ollama", "transformers",
    "tensorflow",
)

LEGACY_IMPORT_ROOTS = ("spine", "sentinel", "raavan", "corpora", "evals")

ALLOWED_IMPORT_ROOTS = {
    "apps/citizen": ("apps.citizen", "packages"),
    "apps/infra": ("apps.infra", "packages", "sentinel"),
    "packages": ("packages", "spine", "sentinel", "raavan", "corpora", "evals"),
}

__all__ = [
    "APP_NAMES", "VIGIL_RUNTIME_ROOT", "FORBIDDEN_CROSS_APP_ROOTS",
    "FORBIDDEN_APP_BYPASS_ROOTS", "FORBIDDEN_LIVE_EXECUTOR_ROOTS",
    "LEGACY_IMPORT_ROOTS", "ALLOWED_IMPORT_ROOTS",
]
