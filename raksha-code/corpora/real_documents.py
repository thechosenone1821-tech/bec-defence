"""Part 4 Phase 5 — run the organ over text that was NOT authored for it.

The corpus in Phase 4 was written by the same person who wrote the detectors.
This phase's only genuine piece of out-of-sample evidence is the project's own
documentation: ~50k words accumulated over months for purposes that had nothing
to do with Bragg peaks or Fiedler connectivity.

**What this is.** Text that is real, unlabelled-for-this-purpose, and would
arrive at an AI reader in exactly this form (a repository an agent is asked to
read). If the firewall cannot pass these, it cannot be deployed in front of any
agent that reads documentation.

**What this is not.** Captured *traffic*. It is not network sessions, not cursor
telemetry, not hidden states, not power readings. Only Organ 3 takes text, so
only Organ 3 can be measured against it. That limitation is the phase's
headline: six of eight organs have no real data of any kind in this repository.
"""

from __future__ import annotations

import glob
import os
import statistics
import sys
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
REPO = os.path.dirname(CODE)
if CODE not in sys.path:
    sys.path.insert(0, CODE)


# A document above this size cannot be screened on a normal machine: the organ
# allocates an n x n float64 matrix, so 6,000 tokens is ~0.3 GB *per matrix* and
# screen() holds several. Screening the 11.6k-word Phase 4 spec was enough to
# OOM a 4 GB container — which is §6.1's defect, measured, not a test harness
# problem to be papered over. Documents over the cap are recorded as
# `skipped_too_large` with their size, so the count is never silently reduced.
SIZE_CAP_TOKENS = 6000


def collect_documents(min_words: int = 40) -> List[Tuple[str, str]]:
    """Every markdown document in the repository, as (path, text)."""
    docs: List[Tuple[str, str]] = []
    for path in glob.glob(os.path.join(REPO, "**", "*.md"), recursive=True):
        if "node_modules" in path:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        if len(text.split()) >= min_words:
            docs.append((os.path.relpath(path, REPO), text))
    return sorted(docs)


def measure(docs: List[Tuple[str, str]], isolate_rules: bool = True) -> Dict[str, Any]:
    """Screen every document, and record why each verdict happened.

    Documents above ``SIZE_CAP_TOKENS`` are skipped and listed separately. That
    is a *concession to the organ's quadratic memory*, and the report says so
    rather than quietly shrinking the corpus.
    """
    from sentinel.shields.ring2_ai_defense import BraggFFTFirewall

    skipped = [(p, len(t.split())) for p, t in docs if len(t.split()) > SIZE_CAP_TOKENS]
    docs = [(p, t) for p, t in docs if len(t.split()) <= SIZE_CAP_TOKENS]

    rows: List[Dict[str, Any]] = []
    for path, text in docs:
        organ = BraggFFTFirewall()
        result = organ.screen(text, agent_id="doc_reader",
                              doc_hash=f"sha256:{os.path.basename(path)}")
        organ.drain_events()
        rows.append({
            "path": path,
            "words": len(text.split()),
            "allowed": bool(result["allowed"]),
            "flags": list(result["flags"]),
            "bragg_peak_ratio": result["bragg_peak_ratio"],
            "fiedler_lambda2": result["fiedler_lambda2"],
        })

    n = len(rows)
    blocked = [r for r in rows if not r["allowed"]]
    peaks = [r["bragg_peak_ratio"] for r in rows]
    lams = [r["fiedler_lambda2"] for r in rows]
    by_peak = sum(1 for r in blocked if "BRAGG_PEAK" in r["flags"])
    by_fiedler = sum(1 for r in blocked if "FIEDLER_FRACTURE" in r["flags"])

    # Isolate the cause of each block by re-screening with one rule disabled.
    # This is the expensive part (~3x the whole corpus), so it is optional: the
    # test suite calls measure() twice and cannot afford it. The default keeps
    # it on so the published report always explains its own numbers.
    peak_only_blocks = None
    fiedler_only_blocks = None
    if isolate_rules:
        peak_only_blocks = 0
        fiedler_only_blocks = 0
        for _, text in docs:
            o1 = BraggFFTFirewall(fiedler_threshold=-1.0)
            if not o1.screen(text)["allowed"]:
                peak_only_blocks += 1
            o1.drain_events()
            o2 = BraggFFTFirewall(bragg_peak_threshold=99.0)
            if not o2.screen(text)["allowed"]:
                fiedler_only_blocks += 1
            o2.drain_events()

    return {
        "n_documents": n,
        "total_words": sum(r["words"] for r in rows),
        "blocked": len(blocked),
        "blocked_pct": (len(blocked) / n) if n else None,
        "flagged_by_peak": by_peak,
        "flagged_by_fiedler": by_fiedler,
        "peak_only_would_block": peak_only_blocks,
        "fiedler_only_would_block": fiedler_only_blocks,
        "peak_median": statistics.median(peaks) if peaks else None,
        "peak_max": max(peaks) if peaks else None,
        "lambda2_median": statistics.median(lams) if lams else None,
        "rows": rows,
        "size_cap_tokens": SIZE_CAP_TOKENS,
        "skipped_too_large": skipped,
    }


def main() -> int:
    docs = collect_documents()
    report = measure(docs)
    print("# Organ 3 against real, unlabelled project documentation\n")
    print(f"documents: {report['n_documents']}   words: {report['total_words']:,}")
    print(f"blocked:   {report['blocked']}/{report['n_documents']} "
          f"({report['blocked_pct']:.0%})")
    print(f"  flagged by BRAGG_PEAK:      {report['flagged_by_peak']}")
    print(f"  flagged by FIEDLER_FRACTURE:{report['flagged_by_fiedler']}")
    print(f"  with the peak rule alone:   {report['peak_only_would_block']} blocked")
    print(f"  with the Fiedler rule alone:{report['fiedler_only_would_block']} blocked")
    print(f"peak median {report['peak_median']:.3f}  max {report['peak_max']:.3f}")
    print(f"lambda2 median {report['lambda2_median']:.4f}")
    if report["skipped_too_large"]:
        print(f"\nskipped above {report['size_cap_tokens']} tokens "
              f"(organ memory is quadratic):")
        for path, n in report["skipped_too_large"]:
            print(f"  {path} ({n:,} tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
