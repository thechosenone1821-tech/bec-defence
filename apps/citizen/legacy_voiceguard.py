"""Read-only adapter to the frozen VoiceGuard/MAYA seam.

Phase 2 created this adapter without editing or moving VoiceGuard/MAYA. Phase 4
does **not** use it on the active Citizen path: ``voiceguard_interface.py`` is a
disabled, documented seam and ``tools/check_phase4_citizen.py`` rejects any other
app-owned import of ``citizen.voiceguard``. This file remains the single allowed
read-only adapter for a future Phase 11.
"""
from __future__ import annotations

from citizen.voiceguard import contract as VC
from citizen.voiceguard import i18n
from citizen.voiceguard import score_voice
from citizen.voiceguard.capture import (
    MAX_SCREEN_SAMPLES,
    RING_SAMPLES,
    retention_policy,
    screen_with_consent,
)
from citizen.voiceguard.i18n import render_source

normalise_language = i18n.normalise_language
explain_message = i18n.explain_message
explain = i18n.explain
explain_report = i18n.explain_report
LANGUAGES = i18n.LANGUAGES
DEFAULT_LANGUAGE = i18n.DEFAULT_LANGUAGE

__all__ = [
    "VC", "i18n", "score_voice", "MAX_SCREEN_SAMPLES", "RING_SAMPLES",
    "retention_policy", "screen_with_consent", "render_source",
    "normalise_language", "explain_message", "explain", "explain_report",
    "LANGUAGES", "DEFAULT_LANGUAGE",
]
