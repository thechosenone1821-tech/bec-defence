"""Machine-readable Phase 2/3 separation and no-bypass contract."""
from __future__ import annotations

APP_NAMES = ("citizen", "infra")

FORBIDDEN_CROSS_APP_ROOTS = {
    "citizen": ("apps.infra", "apps.infra.backend", "apps.infra.detectors", "sentinel", "raavan", "corpora", "evals", "spine"),
    "infra": ("apps.citizen", "apps.citizen.api", "apps.citizen.messageguard", "apps.citizen.risk", "citizen", "spine"),
}

FORBIDDEN_APP_BYPASS_ROOTS = (
    "spine.bus", "spine.governor", "spine.ledger", "spine.containment",
    "spine.sanitizer", "spine.entity_graph", "spine.orchestrator",
    "sentinel.shields.base_organ.handle_rpc",
)

# Phase 4: no Citizen app module may reach an AI/ML model or the Commander.
FORBIDDEN_AI_MODEL_ROOTS = (
    "spine.slm_client", "spine.orchestrator", "spine.orchestrator.SLMClient",
    "citizen.voiceguard.model", "citizen.voiceguard.voiceguard",
    "citizen.voiceguard.train", "citizen.voiceguard.corpus",
    "ollama", "transformers", "torch", "tensorflow",
)

# The only app-owned file allowed to import the frozen VoiceGuard seam.
CITIZEN_VOICEGUARD_ADAPTER = "apps/citizen/legacy_voiceguard.py"

FROZEN_SEAM_ROOTS = ("citizen.voiceguard",)
LEGACY_IMPORT_ROOTS = ("spine", "sentinel", "raavan", "corpora", "evals")

ALLOWED_IMPORT_ROOTS = {
    "apps/citizen": ("apps.citizen", "packages", "citizen.voiceguard"),
    "apps/infra": ("apps.infra", "packages", "sentinel"),
    "packages": ("packages", "spine", "sentinel", "raavan", "corpora", "evals"),
}

__all__ = [
    "APP_NAMES", "FORBIDDEN_CROSS_APP_ROOTS", "FORBIDDEN_APP_BYPASS_ROOTS",
    "FROZEN_SEAM_ROOTS", "LEGACY_IMPORT_ROOTS", "ALLOWED_IMPORT_ROOTS",
    "FORBIDDEN_AI_MODEL_ROOTS", "CITIZEN_VOICEGUARD_ADAPTER",
]
