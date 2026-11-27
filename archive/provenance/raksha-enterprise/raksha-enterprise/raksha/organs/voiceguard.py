"""voiceguard — synthetic-voice scam calls on the citizen leg."""

from __future__ import annotations

from typing import Any

from .base import Organ, _num


class VoiceGuard(Organ):
    name = "voiceguard"

    def evaluate(self, payload: dict[str, Any]) -> tuple[bool, str | None]:
        synth = _num(payload, "synth_score", 0.0)
        reputation = _num(payload, "caller_reputation", 1.0)
        if synth > 0.75 and reputation < 0.5:
            return True, "VG-SYNTH-01"
        return False, None
