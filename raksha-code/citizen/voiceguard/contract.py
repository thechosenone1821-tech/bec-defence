"""MAYA / VoiceGuard — verdict contract, bands, and reason codes.

Frozen surface. Everything downstream (the model, the risk engine, the PWA)
agrees with this module, so changing anything here is a **contract version
bump**, not a refactor.

Design rules (see MAYA_BUILD.md §3):
  * We fail to ``INCONCLUSIVE``, never to a confident "this is genuine".
  * Every non-trivial verdict carries machine-readable reason *codes* plus
    parameters — never free text, never a raw score with no sentence.
  * ``LIKELY_SYNTHETIC`` is gated on a calibrated model. Until Phase 3 ships
    one, :func:`may_claim_clone_detection` returns False and the verdict is
    unreachable by construction (a test enforces this).
"""

from __future__ import annotations

from typing import Any, Dict, Final, Tuple

CONTRACT_VERSION: Final[str] = "voiceguard-contract-v1"

# --------------------------------------------------------------------------- #
# Verdicts. Ordered from "nothing to say" to "actionable warning".
# ``INCONCLUSIVE`` is deliberately NOT the lowest: it means "cannot judge",
# which is a different statement from "quiet input".
# --------------------------------------------------------------------------- #
SILENT: Final[str] = "SILENT"
INCONCLUSIVE: Final[str] = "INCONCLUSIVE"
SUSPICIOUS: Final[str] = "SUSPICIOUS"
LIKELY_SYNTHETIC: Final[str] = "LIKELY_SYNTHETIC"
ERROR: Final[str] = "ERROR"

VERDICTS: Final[Tuple[str, ...]] = (SILENT, INCONCLUSIVE, SUSPICIOUS,
                                    LIKELY_SYNTHETIC, ERROR)

# Escalation order used for aggregation and for the UI's sort.
_ORDER: Final[Dict[str, int]] = {
    ERROR: 0,          # cannot judge — not an accusation, but not calm either
    SILENT: 0,
    INCONCLUSIVE: 1,
    SUSPICIOUS: 2,
    LIKELY_SYNTHETIC: 3,
}

# Verdicts that may be shown to a citizen as "act on this".
ACTIONABLE: Final[frozenset] = frozenset({SUSPICIOUS, LIKELY_SYNTHETIC})

# --------------------------------------------------------------------------- #
# Reason codes. Keys are stable; the sentence lives in the i18n catalogue.
# A reason is (code, params) — params are numbers/strings the renderer slots in.
# --------------------------------------------------------------------------- #
R_TOO_SHORT: Final[str] = "TOO_SHORT"
R_SILENT: Final[str] = "SILENT_AUDIO"
R_INVALID_PAYLOAD: Final[str] = "INVALID_PAYLOAD"
R_PURE_TONE: Final[str] = "PURE_TONE"
R_WHITE_NOISE: Final[str] = "WHITE_NOISE"
R_CLIPPED: Final[str] = "CLIPPED_AUDIO"
R_MONOTONE_PITCH: Final[str] = "MONOTONE_PITCH"
R_MECHANICAL_PAUSES: Final[str] = "MECHANICAL_PAUSES"
R_NO_BREATH: Final[str] = "NO_BREATH_SOUNDS"
R_SPECTRAL_REGULARITY: Final[str] = "SPECTRAL_REGULARITY"
R_MODEL_CLONE: Final[str] = "MODEL_FLAGGED_SYNTHETIC"
R_MODEL_CLEAN: Final[str] = "MODEL_FOUND_NOTHING"
R_NO_MODEL: Final[str] = "NO_TRAINED_MODEL"
R_LOW_CONFIDENCE: Final[str] = "LOW_CONFIDENCE"
R_INTERNAL_ERROR: Final[str] = "INTERNAL_ERROR"

# --------------------------------------------------------------------------- #
# Honesty gate. A build may only claim clone detection when a trained model is
# actually present AND measured. Phase 1–2 ship without one; Phase 3 ships a
# model trained on a synthetic corpus; Phase 5 is where the claim (and this
# constant) may finally change — as its own changelog entry.
# --------------------------------------------------------------------------- #
TRAINED_MODEL_PRESENT: Final[bool] = True     # Phase 3: maya-lr-v1 loads
MEASURED_ON_REAL_SPEECH: Final[bool] = False  # ...on a SYNTHETIC corpus only


def may_claim_clone_detection() -> bool:
    """True only if a trained model exists AND has been measured on real data.

    Two separate facts, both required. Phase 3 satisfies the first and cannot
    satisfy the second — there is no real corpus in this repository — so this
    still returns False. Removing it requires MAYA_BUILD.md §6 in full.
    """
    return TRAINED_MODEL_PRESENT and MEASURED_ON_REAL_SPEECH


def engine_label(model_id: str | None = None) -> str:
    """The string every payload carries so no result can be misread.

    Never remove the honesty clause without setting the gate above.
    """
    if model_id and may_claim_clone_detection():
        return f"maya {model_id} (trained anti-spoof model, measured)"
    if model_id:
        return (f"maya {model_id} (trained on SYNTHETIC corpus — "
                f"real-world accuracy UNMEASURED; NOT a validated anti-spoof model)")
    return "maya-spectral-v1 (heuristic — NOT a trained anti-spoof model)"


def is_valid_verdict(value: Any) -> bool:
    return isinstance(value, str) and value in VERDICTS


def severity_rank(verdict: str) -> int:
    """Sort key; unknown verdicts sort lowest rather than silently ranking high."""
    return _ORDER.get(verdict, 0)


def max_verdict(verdicts) -> str:
    """Worst (most actionable) verdict in an iterable. Empty ⇒ INCONCLUSIVE."""
    items = [v for v in verdicts if is_valid_verdict(v)]
    if not items:
        return INCONCLUSIVE
    return max(items, key=severity_rank)


# --------------------------------------------------------------------------- #
def reason(code: str, **params: Any) -> Dict[str, Any]:
    """Build a structured reason. ``code`` must be one of the R_* constants."""
    return {"code": code, "params": params}
