"""Phase 9 — one canonical MessageGuard measurement implementation.

The legacy ``raksha-code/evals/messageguard/run_evals.py`` is now a thin
compatibility CLI that imports this module. Every published number is computed
from the one hand-authored corpus with the one shipped scorer. Real-world recall
and false-positive rate remain UNMEASURED.
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
CODE_ROOT = ROOT / "raksha-code"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.citizen.messageguard import ENGINE, analyze  # noqa: E402

FIXTURES = CODE_ROOT / "citizen" / "fixtures" / "messageguard"

MODERATE, HIGH = 0.20, 0.70
LANG_ORDER = ("en", "hi", "te", "hinglish")
FAMILIES = ["credential", "authority", "money_action", "prize", "urgency", "link_grab"]
MEASUREMENT_SCOPE = (
    "hand-authored / in-distribution; real-world recall and FPR UNMEASURED"
)


def load_jsonl(path: pathlib.Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def compute_results() -> Dict[str, Any]:
    scam_by_lang: Dict[str, List[Dict[str, Any]]] = {lang: [] for lang in LANG_ORDER}
    benign_by_lang: Dict[str, List[Dict[str, Any]]] = {lang: [] for lang in LANG_ORDER}
    for path in sorted(FIXTURES.glob("*.jsonl")):
        for rec in load_jsonl(path):
            lang = rec["lang"]
            if lang not in LANG_ORDER:
                raise ValueError(f"unexpected corpus language: {lang!r}")
            detector_lang = "hinglish" if lang == "hinglish" else "auto"
            rec["_result"] = analyze(rec["text"], lang=detector_lang)
            if rec["label"] == "scam":
                scam_by_lang[lang].append(rec)
            else:
                benign_by_lang[lang].append(rec)

    results: Dict[str, Any] = {
        "condition": MEASUREMENT_SCOPE,
        "status": "ok",
        "measurement_scope": MEASUREMENT_SCOPE,
        "engine": ENGINE,
        "detector_interface": "apps/citizen/messageguard",
        "reason_catalogue": "packages/contracts/reasons.py",
        "generated_report": "EVALS.md",
        "corpus": {
            "claim_scope": MEASUREMENT_SCOPE,
            "scam_total": sum(len(v) for v in scam_by_lang.values()),
            "benign_total": sum(len(v) for v in benign_by_lang.values()),
            "fixture_total": sum(len(v) for v in scam_by_lang.values()) + sum(len(v) for v in benign_by_lang.values()),
            "scam_by_lang": {k: len(v) for k, v in scam_by_lang.items()},
            "benign_by_lang": {k: len(v) for k, v in benign_by_lang.items()},
        },
        "languages": {},
        "family_recall": {},
        "benign_fp_cases": [],
    }

    for lang in LANG_ORDER:
        scam = scam_by_lang[lang]
        benign = benign_by_lang[lang]

        caught_mod = sum(1 for r in scam if r["_result"]["score"] >= MODERATE)
        caught_high = sum(1 for r in scam if r["_result"]["score"] >= HIGH)
        crit = sum(1 for r in scam if r["_result"]["verdict"] == "CRITICAL")

        fp_mod = [r for r in benign if r["_result"]["score"] >= MODERATE]
        fp_high = [r for r in benign if r["_result"]["score"] >= HIGH]

        fam = {}
        for family in FAMILIES:
            labelled = [r for r in scam if family in r.get("families", [])]
            hit = [r for r in labelled if family in r["_result"]["families_fired"]]
            fam[family] = {
                "labelled": len(labelled),
                "hit": len(hit),
                "recall": round(len(hit) / len(labelled), 4) if labelled else None,
            }

        tn_mod = len(benign) - len(fp_mod)
        results["languages"][lang] = {
            "scam_caught_moderate": caught_mod,
            "scam_caught_high": caught_high,
            "scam_total": len(scam),
            "detection_rate_moderate": round(caught_mod / len(scam), 4),
            "detection_rate_high": round(caught_high / len(scam), 4),
            "critical_count": crit,
            "benign_total": len(benign),
            "fp_moderate": len(fp_mod),
            "fp_high": len(fp_high),
            "fpr_moderate": round(len(fp_mod) / len(benign), 4),
            "fpr_high": round(len(fp_high) / len(benign), 4),
            "tn_moderate": tn_mod,
            "family_recall": fam,
            "fp_cases": [
                {
                    "id": r["id"],
                    "kind": r.get("kind") or r.get("category") or "unclassified",
                    "score": r["_result"]["score"],
                    "verdict": r["_result"]["verdict"],
                    "families_fired": r["_result"]["families_fired"],
                    "text": r["text"],
                }
                for r in fp_mod
            ],
        }
        results["benign_fp_cases"].extend(
            {"lang": lang, **c} for c in results["languages"][lang]["fp_cases"]
        )

    all_scam = [r for lang in LANG_ORDER for r in scam_by_lang[lang]]
    for family in FAMILIES:
        labelled = [r for r in all_scam if family in r.get("families", [])]
        hit = [r for r in labelled if family in r["_result"]["families_fired"]]
        results["family_recall"][family] = {
            "labelled": len(labelled),
            "hit": len(hit),
            "recall": round(len(hit) / len(labelled), 4) if labelled else None,
        }

    total_scam = results["corpus"]["scam_total"]
    total_benign = results["corpus"]["benign_total"]
    tp = sum(results["languages"][l]["scam_caught_moderate"] for l in LANG_ORDER)
    tn = sum(results["languages"][l]["tn_moderate"] for l in LANG_ORDER)
    fp = sum(results["languages"][l]["fp_moderate"] for l in LANG_ORDER)
    fn = total_scam - tp
    results["overall"] = {
        "claim_scope": MEASUREMENT_SCOPE,
        "tp_moderate": tp,
        "tn_moderate": tn,
        "fp_moderate": fp,
        "fn_moderate": fn,
        "accuracy_moderate": round((tp + tn) / (total_scam + total_benign), 4),
        "precision_moderate": round(tp / (tp + fp), 4) if (tp + fp) else None,
        "recall_moderate": round(tp / total_scam, 4),
        "fpr_moderate": round(fp / total_benign, 4),
    }
    return results
