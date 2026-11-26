"""CLI: assess one message from the command line.

    python -m raksha.messageguard "your card is blocked, click bit.ly/x to verify"
    python -m raksha.messageguard --lang hi "आपका OTP बताइए, वरना खाता बंद हो जाएगा"
    python -m raksha.messageguard --json --legacy "..."
"""

from __future__ import annotations

import argparse
import json
import sys

from .legacy_organ import to_legacy_organ_payload
from .scorer import assess
from .types import Band


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m raksha.messageguard",
        description="Deterministic offline scam-script detector (Part 3).",
    )
    parser.add_argument("text", nargs="+", help="the message text to assess")
    parser.add_argument(
        "--lang",
        choices=["auto", "en", "hi", "te", "hinglish"],
        default="auto",
        help="matching language (default: auto-detect by script)",
    )
    parser.add_argument("--json", action="store_true", help="print the full verdict as JSON")
    parser.add_argument("--legacy", action="store_true", help="print the legacy organ RPC payload too")
    parser.add_argument(
        "--citizen-lang",
        choices=["en", "hi", "te"],
        default=None,
        help="language for the citizen-facing summary (default: message language)",
    )
    args = parser.parse_args(argv)

    text = " ".join(args.text)
    lang = None if args.lang == "auto" else args.lang
    verdict = assess(text, lang=lang)

    if args.json:
        print(json.dumps(verdict.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Band    : {verdict.band.value}")
        print(f"Score   : {verdict.score:.2f}" + ("  (x1.3 multi-family boost applied)" if verdict.boosted else ""))
        print(f"Language: {verdict.lang}")
        if verdict.families:
            weights = ", ".join(f"{f}({verdict.family_hits[f]} hits)" for f in verdict.families)
            print(f"Families: {weights}")
        else:
            print("Families: none")
        if verdict.reasons:
            print("Reasons :")
            for r in verdict.reasons:
                print(f"  [{r.family}] {r.matched}")
        citizen = verdict.citizen(args.citizen_lang)
        print(f"Citizen ({citizen['lang']}): {citizen['band_label']}")
        print(f"          {citizen['advice']}")
        for line in citizen["reasons"]:
            print(f"          - {line}")

    if args.legacy:
        payload = to_legacy_organ_payload(verdict)
        print("--- legacy organ RPC payload ---")
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
