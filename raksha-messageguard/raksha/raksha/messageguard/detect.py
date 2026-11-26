"""Script-based language detection.

Deliberately simple and deterministic: count letters in the Devanagari,
Telugu and Latin Unicode blocks and return the majority. Real scam SMS mix
scripts freely ("आपका OTP बताइए"), so the matcher never trusts detection for
token selection alone — the scorer merges the English token set into the
Hindi/Telugu universes (see ``tokens.LANG_UNIVERSES``).

Transliterated Hinglish is Latin script and indistinguishable from English
by script; it detects as ``en``. Because ``en`` and ``hinglish`` share the
same matching universe, no harm is done.
"""

from __future__ import annotations

_DEVANAGARI = range(0x0900, 0x0980)
_TELUGU = range(0x0C00, 0x0C80)

__all__ = ["detect_language", "SCRIPT_LANGS"]


def _count_in(text: str, ranges: tuple[range, ...]) -> int:
    total = 0
    for ch in text:
        code = ord(ch)
        if any(lo <= code <= hi for lo, hi in [(r[0], r[-1]) for r in ranges]):
            total += 1
    return total


def detect_language(text: str) -> str:
    """Return "hi", "te" or "en" for a message, by dominant script."""
    dev = sum(1 for ch in text if ord(ch) in _DEVANAGARI)
    tel = sum(1 for ch in text if ord(ch) in _TELUGU)
    lat = sum(1 for ch in text if ("a" <= ch <= "z") or ("A" <= ch <= "Z"))
    if tel > dev and tel >= lat:
        return "te"
    if dev > tel and dev >= lat:
        return "hi"
    return "en"


SCRIPT_LANGS: tuple[str, ...] = ("en", "hi", "te")
