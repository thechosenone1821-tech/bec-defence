"""Deterministic language detection for the one MessageGuard interface.

The detector language is a *matching* choice, not a citizen copy language.
Devanagari and Telugu are selected by script. Latin-script Hinglish is
separated from English with a small, auditable romanized-Hindi cue list; the
CLI can then opt into the dedicated Hinglish token set. The Citizen API still
uses ``lang="auto"`` for en/hi/te plus language-agnostic patterns, so adding
Hinglish does not silently change the published en/hi/te measurement.

No model, network, or device metadata is used.
"""
from __future__ import annotations

import re

__all__ = ["SCRIPT_LANGS", "SUPPORTED_LANGS", "detect_language"]

SCRIPT_LANGS = ("en", "hi", "te", "hinglish")
SUPPORTED_LANGS = ("auto",) + SCRIPT_LANGS

_DEVANAGARI = (0x0900, 0x097F)
_TELUGU = (0x0C00, 0x0C7F)
_LATIN = re.compile(r"[a-z]", re.IGNORECASE)

# Strong, common romanized-Hindi function words and scam-script verbs. Two
# distinct cues are required so ordinary English SMS is not misclassified.
_HINGLISH_CUES = re.compile(
    r"\b(?:aap|aapka|aapke|aapki|aapne|apna|apni|khata|khate|karo|karein|"
    r"karne|bhejo|bhej|batao|warna|hai|hain|hue|gaya|gaye|ho|jayega|jayegi|"
    r"jayenge|ghante|aaj|abhi|paise|paisa|chahiye|mat|nahi|nahin|kabhi|"
    r"jaldi|turant|bolo|beta|denge|dena|dekhein|jayein|par|se|ko|me|liye|"
    r"tak|sath|kisi|baat|darj|jama|bakaya|nikale|kharch|kate|due|off|"
    r"shop|book|continue|update|kyc|emi|bill|receipt|document|delivery)\b",
    re.IGNORECASE,
)


def _count_script(text: str, low: int, high: int) -> int:
    return sum(1 for ch in text if low <= ord(ch) <= high)


def detect_language(text: str) -> str:
    """Return ``en``, ``hi``, ``te`` or ``hinglish`` by script and cues.

    Script majority wins for Devanagari/Telugu. Latin text becomes Hinglish
    when at least two distinct romanized-Hindi cues are present; otherwise
    it is English. Detection is deliberately conservative and is never used
    to justify a field-performance claim.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    dev = _count_script(text, *_DEVANAGARI)
    tel = _count_script(text, *_TELUGU)
    lat = len(_LATIN.findall(text))
    if tel > dev and tel >= lat:
        return "te"
    if dev > tel and dev >= lat:
        return "hi"
    cues = {m.group(0).casefold() for m in _HINGLISH_CUES.finditer(text)}
    if len(cues) >= 2:
        return "hinglish"
    return "en"
