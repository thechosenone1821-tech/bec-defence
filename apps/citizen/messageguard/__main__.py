"""Operator CLI for the one canonical MessageGuard interface.

Examples::

    python -m apps.citizen.messageguard "Share your OTP now, else account blocked"
    python -m apps.citizen.messageguard --lang hinglish "Aapka OTP batao warna account band"
    python -m apps.citizen.messageguard --json --legacy --citizen-lang hi "..."

This is a deterministic, offline developer/operator diagnostic. It deliberately
omits raw scores, matched phrases and reason details from every output, because
those are not citizen-facing explanations. The Citizen API remains the only
runtime UI path and never forwards message text off the phone.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from apps.citizen.copy import explain_message
from packages.contracts.i18n import LANGUAGES

from . import ENGINE, SUPPORTED_LANGS, detect_language, score_message
from .legacy_organ import to_legacy_organ_payload

__all__ = ["main"]


def _display_lang(detected: str, override: Optional[str]) -> str:
    if override:
        return override
    if detected == "hinglish":
        return "hi"
    return detected if detected in LANGUAGES else "en"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m apps.citizen.messageguard",
        description="Deterministic offline MessageGuard operator CLI.",
        epilog="Operator diagnostics only; no raw score or matched phrase is printed.",
    )
    parser.add_argument("text", nargs="+", help="the message text to assess")
    parser.add_argument("--lang", choices=SUPPORTED_LANGS, default="auto",
                        help="detector language (default: auto; Hinglish uses explicit tokens)")
    parser.add_argument("--json", action="store_true",
                        help="print a sanitized JSON verdict/citizen summary")
    parser.add_argument("--legacy", action="store_true",
                        help="also print the mapped legacy organ RPC payload")
    parser.add_argument("--citizen-lang", choices=LANGUAGES, default=None,
                        help="citizen copy language (default: detected display language)")
    args = parser.parse_args(argv)

    text = " ".join(args.text)[:4000]
    if args.lang == "auto":
        detected = detect_language(text)
        detector_lang = "hinglish" if detected == "hinglish" else "auto"
    else:
        detected = args.lang
        detector_lang = args.lang

    result = score_message(text, lang=detector_lang)
    display_lang = _display_lang(detected, args.citizen_lang)
    citizen = explain_message(result, display_lang)
    payload = to_legacy_organ_payload(result).to_dict() if args.legacy else None

    safe = {
        "engine": ENGINE,
        "detector_lang": result["detector_lang"],
        "verdict": result["verdict"],
        "families": result["families_hit"],
        "message_reason_codes": citizen["message_reason_codes"],
        "citizen": citizen,
    }
    if payload is not None:
        safe["legacy_organ"] = payload

    if args.json:
        print(json.dumps(safe, ensure_ascii=False, indent=2))
    else:
        print(f"Verdict : {result['verdict']}")
        print(f"Language: {result['detector_lang']}")
        print(f"Families: {', '.join(result['families_hit']) or 'none'}")
        print(f"Citizen ({citizen['lang']}): {citizen['title']}")
        print(f"Action  : {citizen['action']}")
        print(f"Helpline: {citizen['helpline']}")
        for sentence in citizen["reasons"]:
            print(f"  - {sentence}")
        print(f"Disclaimer: {citizen['disclaimer']}")
        if payload is not None:
            print("--- legacy organ RPC payload (operator only) ---")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
