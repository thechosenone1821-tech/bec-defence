"""Evaluation harness for MessageGuard (Part 3).

Run from the repo root:

    python -m raksha.evals.run_evals            # tables + results files
    python -m raksha.evals.run_evals --review   # + full false-positive listing
    python -m raksha.evals.run_evals --quiet    # only gates

Measures exactly what the Part 3 definition of done requires:
    - scam detection per language (score >= MODERATE 0.20 / >= HIGH 0.45)
    - false-positive rate on GENUINE messages (benign corpus), overall and on
      the genuine-bank-alert subset only
    - determinism (two passes, identical verdict hash)
    - corpus gates (>= 300 scam fixtures with per-language coverage)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from raksha.messageguard import assess
from raksha.messageguard.types import Band

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "corpus"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

LANGS = ("en", "hi", "te", "hinglish")
GAP_CATEGORY = "obfuscation_gap"
BANK_ALERT_CATEGORIES = {
    "bank_txn",
    "otp_notice",
    "kyc_official",
    "loan_emi",
    "salary",
    "bill_receipt",
    "bank_fraud_alert",
}

# Definition-of-done gates (spec section 5). These encode the published targets.
GATES = {
    "scam_fixtures_ge_300": lambda r: r["corpus"]["scam_total"] >= 300,
    "per_language_coverage": lambda r: all(
        r["corpus"]["scam_by_lang"][lang] >= 20 for lang in LANGS
    ),
    "benign_bank_alerts_ge_60": lambda r: r["corpus"]["benign_bank_alerts"] >= 60,
    "detection_high_excl_gap_ge_0.90": lambda r: (
        r["detection"]["excl_gap"]["det_high"] >= 0.90
    ),
    "fp_high_bank_alerts_le_0.10": lambda r: (
        r["false_positives"]["bank_alerts"]["fp_high"] <= 0.10
    ),
}

__all__ = ["load_corpus", "run_evaluation", "GATES", "BANK_ALERT_CATEGORIES"]


def load_corpus(corpus_dir: Path | None = None) -> list[dict]:
    corpus_dir = corpus_dir or CORPUS_DIR
    fixtures: list[dict] = []
    for path in sorted(corpus_dir.glob("*.jsonl")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row["_file"] = path.name
            row["_line"] = line_no
            fixtures.append(row)
    return fixtures


def _pct(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def _score_row(fix: dict) -> dict:
    verdict = assess(fix["text"], lang=fix["lang"])
    signature = json.dumps(
        [verdict.score, verdict.band.value, list(verdict.families)]
        + [[r.code, r.matched] for r in verdict.reasons],
        ensure_ascii=False,
        sort_keys=True,
    )
    return {
        "id": fix["id"],
        "lang": fix["lang"],
        "label": fix["label"],
        "category": fix["category"],
        "score": verdict.score,
        "band": verdict.band.value,
        "families": list(verdict.families),
        "reasons": [[r.family, r.trigger, r.matched] for r in verdict.reasons],
        "_signature": signature,
    }


def _scam_block(rows: list[dict]) -> dict:
    n = len(rows)
    bands = Counter(r["band"] for r in rows)
    return {
        "n": n,
        "mean_score": round(sum(r["score"] for r in rows) / n, 3) if n else 0.0,
        "bands": {b.value: bands[b.value] for b in Band},
        "det_moderate": _pct(sum(1 for r in rows if r["score"] >= 0.20), n),
        "det_high": _pct(sum(1 for r in rows if r["score"] >= 0.45), n),
    }


def run_evaluation(corpus_dir: Path | None = None) -> dict:
    fixtures = load_corpus(corpus_dir)
    rows = [_score_row(f) for f in fixtures]

    # determinism: re-score everything and compare signatures
    rows2 = [_score_row(f) for f in fixtures]
    digest = hashlib.sha256(
        json.dumps(sorted(r["_signature"] for r in rows), ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]
    digest2 = hashlib.sha256(
        json.dumps(sorted(r["_signature"] for r in rows2), ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]

    scam = [r for r in rows if r["label"] == "scam"]
    benign = [r for r in rows if r["label"] == "benign"]
    bank = [r for r in benign if r["category"] in BANK_ALERT_CATEGORIES]

    # ---- scam detection -----------------------------------------------------
    detection: dict = {
        "all": _scam_block(scam),
        "excl_gap": _scam_block([r for r in scam if r["category"] != GAP_CATEGORY]),
        "gap_only": _scam_block([r for r in scam if r["category"] == GAP_CATEGORY]),
        "by_lang": {},
    }
    for lang in LANGS:
        sub = [r for r in scam if r["lang"] == lang]
        sub_core = [r for r in sub if r["category"] != GAP_CATEGORY]
        detection["by_lang"][lang] = {
            "all": _scam_block(sub),
            "excl_gap": _scam_block(sub_core),
        }

    # per-category detection (where do we still miss?)
    by_category: dict[str, dict] = {}
    for cat in sorted({r["category"] for r in scam}):
        sub = [r for r in scam if r["category"] == cat]
        by_category[cat] = _scam_block(sub)
    detection["by_category"] = by_category

    # family fire-rate on the scam corpus (sanity: which families do the work)
    family_rate: dict[str, float] = {}
    for family in ("credential", "authority", "money_action", "prize", "urgency", "link_grab"):
        family_rate[family] = _pct(sum(1 for r in scam if family in r["families"]), len(scam))

    # ---- false positives on genuine messages --------------------------------
    fp_rows = [r for r in benign if r["score"] >= 0.20]
    fp_bank_rows = [r for r in bank if r["score"] >= 0.20]

    false_positives: dict = {
        "all": {
            "n": len(benign),
            "fp_moderate": _pct(sum(1 for r in benign if r["score"] >= 0.20), len(benign)),
            "fp_high": _pct(sum(1 for r in benign if r["score"] >= 0.45), len(benign)),
        },
        "bank_alerts": {
            "n": len(bank),
            "fp_moderate": _pct(sum(1 for r in bank if r["score"] >= 0.20), len(bank)),
            "fp_high": _pct(sum(1 for r in bank if r["score"] >= 0.45), len(bank)),
        },
        "by_lang": {},
        "rows": [],
    }
    for lang in LANGS:
        bl = [r for r in benign if r["lang"] == lang]
        bl_bank = [r for r in bl if r["category"] in BANK_ALERT_CATEGORIES]
        false_positives["by_lang"][lang] = {
            "n": len(bl),
            "fp_moderate": _pct(sum(1 for r in bl if r["score"] >= 0.20), len(bl)),
            "fp_high": _pct(sum(1 for r in bl if r["score"] >= 0.45), len(bl)),
            "bank_n": len(bl_bank),
            "bank_fp_high": _pct(sum(1 for r in bl_bank if r["score"] >= 0.45), len(bl_bank)),
        }
    for r in fp_rows:
        false_positives["rows"].append(
            {
                "id": r["id"],
                "lang": r["lang"],
                "category": r["category"],
                "band": r["band"],
                "score": r["score"],
                "families": r["families"],
                "hits": [f"{fam}: {m}" for fam, trig, m in r["reasons"]][:4],
            }
        )

    # ---- honest miss list (scam fixtures below MODERATE) --------------------
    misses = [
        {"id": r["id"], "lang": r["lang"], "category": r["category"], "score": r["score"]}
        for r in scam
        if r["score"] < 0.20
    ]

    corpus = {
        "total": len(rows),
        "scam_total": len(scam),
        "benign_total": len(benign),
        "scam_by_lang": {lang: sum(1 for r in scam if r["lang"] == lang) for lang in LANGS},
        "benign_by_lang": {lang: sum(1 for r in benign if r["lang"] == lang) for lang in LANGS},
        "benign_bank_alerts": len(bank),
    }

    results = {
        "corpus": corpus,
        "detection": detection,
        "family_fire_rate": family_rate,
        "false_positives": false_positives,
        "scam_misses": misses,
        "determinism": {"verified": digest == digest2, "verdict_hash": digest},
        "gates": {},
    }
    results["gates"] = {name: bool(fn(results)) for name, fn in GATES.items()}
    return results


def _render_md(r: dict) -> str:
    lines: list[str] = []
    lines.append("# MessageGuard evaluation results (generated)\n")
    c = r["corpus"]
    lines.append(f"Corpus: {c['total']} fixtures — scam {c['scam_total']}, benign {c['benign_total']} "
                 f"(genuine bank alerts: {c['benign_bank_alerts']}).\n")
    lines.append("| scam lang | n | det@MODERATE | det@HIGH |")
    lines.append("|---|---|---|---|")
    for lang in LANGS:
        blk = r["detection"]["by_lang"][lang]["excl_gap"]
        lines.append(f"| {lang} | {blk['n']} | {blk['det_moderate']:.1%} | {blk['det_high']:.1%} |")
    blk = r["detection"]["excl_gap"]
    lines.append(f"| **all (excl gap)** | {blk['n']} | **{blk['det_moderate']:.1%}** | **{blk['det_high']:.1%}** |")
    gap = r["detection"]["gap_only"]
    lines.append(f"| known-gap only | {gap['n']} | {gap['det_moderate']:.1%} | {gap['det_high']:.1%} |\n")

    fp = r["false_positives"]
    lines.append("## False positives on genuine messages\n")
    lines.append("| set | n | FP@MODERATE | FP@HIGH |")
    lines.append("|---|---|---|---|")
    a = fp["all"]
    lines.append(f"| all benign | {a['n']} | {a['fp_moderate']:.1%} | {a['fp_high']:.1%} |")
    b = fp["bank_alerts"]
    lines.append(f"| genuine bank alerts | {b['n']} | {b['fp_moderate']:.1%} | {b['fp_high']:.1%} |")
    lines.append("")
    lines.append("### False positives by language (bank-alert subset FP@HIGH)\n")
    lines.append("| lang | benign n | FP@MODERATE | FP@HIGH | bank n | bank FP@HIGH |")
    lines.append("|---|---|---|---|---|---|")
    for lang in LANGS:
        d = fp["by_lang"][lang]
        lines.append(
            f"| {lang} | {d['n']} | {d['fp_moderate']:.1%} | {d['fp_high']:.1%} | "
            f"{d['bank_n']} | {d['bank_fp_high']:.1%} |"
        )
    lines.append("")
    lines.append("### False-positive review listing (all benign fixtures >= MODERATE)\n")
    if fp["rows"]:
        lines.append("| id | lang | category | band | score | fired |")
        lines.append("|---|---|---|---|---|---|")
        for row in fp["rows"]:
            fired = "; ".join(row["hits"])
            lines.append(
                f"| {row['id']} | {row['lang']} | {row['category']} | {row['band']} | "
                f"{row['score']:.2f} | {fired} |"
            )
    else:
        lines.append("(none)")
    lines.append("")
    lines.append(f"Determinism verified: {r['determinism']['verified']} "
                 f"(verdict hash `{r['determinism']['verdict_hash']}`).\n")
    lines.append("## Gates\n")
    for name, ok in r["gates"].items():
        lines.append(f"- [{'x' if ok else ' '}] {name}")
    if r["scam_misses"]:
        lines.append("\n## Scam fixtures scoring below MODERATE (honest misses)\n")
        for m in r["scam_misses"]:
            lines.append(f"- {m['id']} ({m['lang']}, {m['category']}, score {m['score']:.2f})")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m raksha.evals.run_evals")
    parser.add_argument("--corpus", default=None, help="corpus directory (default: ./corpus)")
    parser.add_argument("--review", action="store_true", help="print the full FP listing")
    parser.add_argument("--quiet", action="store_true", help="print only gates and headline numbers")
    parser.add_argument("--no-write", action="store_true", help="do not write results files")
    args = parser.parse_args(argv)

    results = run_evaluation(Path(args.corpus) if args.corpus else None)

    if not args.quiet:
        print(_render_md(results))
    else:
        det = results["detection"]["excl_gap"]
        fp = results["false_positives"]["bank_alerts"]
        print(f"corpus scam={results['corpus']['scam_total']} "
              f"bank_alerts={results['corpus']['benign_bank_alerts']}")
        print(f"detection@HIGH excl gap = {det['det_high']:.1%}")
        print(f"FP@HIGH on bank alerts  = {fp['fp_high']:.1%}")
        print(f"determinism verified    = {results['determinism']['verified']}")
        for name, ok in results["gates"].items():
            print(f"gate {'PASS' if ok else 'FAIL'}: {name}")

    if args.review:
        rows = results["false_positives"]["rows"]
        print(f"\n--- FP review: {len(rows)} benign fixtures >= MODERATE ---")
        for row in rows:
            print(f"{row['id']:22s} {row['lang']:9s} {row['category']:17s} "
                  f"{row['band']:9s} {row['score']:.2f}  {'; '.join(row['hits'])}")

    if not args.no_write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / "latest.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (RESULTS_DIR / "latest.md").write_text(_render_md(results), encoding="utf-8")
        if not args.quiet:
            print(f"\nresults written to {RESULTS_DIR}")

    return 0 if all(results["gates"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
