"""Load a corpus, build each case deterministically, score it, and compare
against a constant-rate baseline and an oracle of the generator parameters.

Design rules, each one the result of something that went wrong earlier in this
project:

1. **Determinism is asserted, not assumed.** Every case is built twice and the
   arrays compared byte-for-byte. A corpus whose cases change between runs
   cannot produce a stable rate, and a rate that moves for no reason is worse
   than no rate.

2. **Every organ is scored at the decision boundary, not at its report dict.**
   The scorer calls the organ's real entry point and asks whether it emitted.
   Nothing reads a self-reported label — the Phase 2 lesson.

3. **The oracle is the generator parameters, not the detector's opinion.**
   ``oracle_expected`` derives from what the case actually is.

4. **A rate is never published without its family breakdown.** Organ 1 in
   particular passes overall while failing on a whole subtype (§4.3).
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

import numpy as np

ORGAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "organs")


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_corpus(name: str) -> Dict[str, Any]:
    path = os.path.join(ORGAN_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"no corpus at {path}")
    with open(path) as f:
        corpus = json.load(f)
    for field in ("organ", "entry_point", "provenance"):
        if field not in corpus:
            raise ValueError(f"{name}: corpus is missing required field {field!r}")
    ids = [c["id"] for c in corpus["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name}: duplicate case ids")
    for case in corpus["cases"]:
        if case["label"] not in ("attack", "benign"):
            raise ValueError(f"{name}:{case['id']} has an unknown label {case['label']!r}")
        # Every case must justify itself, whatever its kind.
        for field in ("generator", "rationale"):
            if field not in case:
                raise ValueError(f"{name}:{case['id']} is missing {field!r}")
        # The matrix fields are only meaningful for kind == "session_matrix".
        # Demanding them of a text or trajectory case was a validation bug: it
        # made the schema describe one kind of corpus rather than all of them.
        if case.get("kind", "session_matrix") == "session_matrix":
            for field in ("bot_direction_spread", "n_bots", "n_benign"):
                if field not in case:
                    raise ValueError(f"{name}:{case['id']} is missing {field!r}")
    return corpus


def list_corpora() -> List[str]:
    return sorted(f for f in os.listdir(ORGAN_DIR) if f.endswith(".json"))


# --------------------------------------------------------------------------- #
# Deterministic case construction
# --------------------------------------------------------------------------- #
def _build_sessions(case: Dict[str, Any], seed: int, dims: int) -> np.ndarray:
    """The reference generator for 'session matrix' corpora (Organ 1).

    Kept here rather than in the organ so that the same routine builds an
    attack case and a benign case. If the organ's author wrote the attack and
    the benign builder separately, the difference between them would be the
    detector, and the report would measure nothing.
    """
    rng = np.random.default_rng(seed)
    n_benign = int(case["n_benign"])
    n_bots = int(case["n_bots"])
    frac = float(case.get("benign_fleet_fraction", 0.0))
    n_fleet = int(round(frac * n_benign))
    n_indep = n_benign - n_fleet

    parts: List[np.ndarray] = []
    if n_indep:
        parts.append(rng.normal(0.0, case["benign_std"], (n_indep, dims))
                     + float(case.get("benign_mean", 0.0)))
    if n_fleet:
        axis = np.zeros(dims)
        axis[0] = 1.0
        parts.append(np.outer(rng.normal(0.0, case["benign_fleet_spread"], n_fleet), axis)
                     + rng.normal(0.0, case["benign_fleet_jitter"], (n_fleet, dims)))
    if n_bots:
        offset = np.asarray(case["bot_offset"], dtype=float)
        if offset.shape[0] < dims:
            offset = np.concatenate([offset, np.zeros(dims - offset.shape[0])])
        bots = rng.normal(0.0, case["bot_std"], (n_bots, dims)) + offset
        spread = float(case["bot_direction_spread"])
        if spread > 0:
            axis = np.zeros(dims)
            axis[0] = 1.0
            bots = bots + np.outer(rng.normal(0.0, spread, n_bots), axis)
        parts.append(bots)
    return np.vstack(parts)


def build_case(case: Dict[str, Any], seed: int = 20261123) -> Any:
    """Compile one case into its input. Deterministic for a given seed."""
    dims = len(case.get("bot_offset") or [5])
    dims = max(dims, 5)
    kind = case.get("kind", "session_matrix")
    if kind == "session_matrix":
        return _build_sessions(case, seed, dims)
    raise ValueError(f"unknown case kind {kind!r}")


def build_identically(case: Dict[str, Any], seed: int = 20261123) -> bool:
    """Assert two builds of one case are byte-identical."""
    a, b = build_case(case, seed), build_case(case, seed)
    return np.array_equal(a, b)


# --------------------------------------------------------------------------- #
# Oracle
# --------------------------------------------------------------------------- #
def oracle_expected(case: Dict[str, Any]) -> bool:
    """The ground truth, from what the case *is* rather than what the organ says."""
    return case["label"] == "attack"


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def score_corpus(
    corpus: Dict[str, Any],
    run_case: Callable[[Dict[str, Any], Any], bool],
    seed: int = 20261123,
    compile_payload: Optional[Callable[[Dict[str, Any], int], Any]] = None,
) -> Dict[str, Any]:
    """Run every case through ``run_case`` and tabulate detections.

    ``run_case(case, built_input) -> bool`` must return whether the *organ*
    fired, obtained by calling the organ's entry point and observing whether it
    emitted an event. It must not return a label the organ printed about itself.

    ``compile_payload`` lets a caller supply the compiler for case kinds beyond
    the built-in matrix kind. Without it, scoring a text corpus raised
    "unknown case kind" — the harness assumed one corpus shape.
    """
    compile_payload = compile_payload or build_case
    rows = []
    for case in corpus["cases"]:
        payload = compile_payload(case, seed)
        fired = bool(run_case(case, payload))
        rows.append({
            "id": case["id"],
            "label": case["label"],
            # "control" cases are excluded from every rate. They exist to test
            # identifiability, not detection: a miss on an unidentifiable case
            # is a property of the information, not a detector fault, and
            # counting it would understate the organ while hiding the reason.
            "role": case.get("role", "scored"),
            "family": case.get("family", "unset"),
            "fired": fired,
            "expected": oracle_expected(case),
            "correct": fired == oracle_expected(case),
            "rationale": case["rationale"],
        })

    controls = [r for r in rows if r["role"] == "control"]
    scored = [r for r in rows if r["role"] == "scored"]
    attacks = [r for r in scored if r["label"] == "attack"]
    benign = [r for r in scored if r["label"] == "benign"]
    tp = sum(1 for r in attacks if r["fired"])
    fn = len(attacks) - tp
    fp = sum(1 for r in benign if r["fired"])
    tn = len(benign) - fp

    return {
        "organ": corpus["organ"],
        "entry_point": corpus["entry_point"],
        "provenance": corpus["provenance"],
        "rows": rows,
        "confusion": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
        "detection_rate": (tp / len(attacks)) if attacks else None,
        "false_positive_rate": (fp / len(benign)) if benign else None,
        # The rate a deployer would act on: of everything that raised, how much
        # was real. A high detection rate with a useless precision is how
        # detectors get switched off (Phase 6's subject).
        "precision": (tp / (tp + fp)) if (tp + fp) else None,
        "n_attack": len(attacks),
        "n_benign": len(benign),
        "n_control": len(controls),
        # Per-family breakdown. A single aggregate rate hides the failure mode
        # that matters: Organ 1 passes on offset-separated botnets and fails on
        # every benign family, and the aggregate alone reads like mediocrity
        # rather than like a detector keyed on the wrong quantity.
        "families": _by_family(scored),
        "controls": controls,
    }


def _by_family(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        fam = out.setdefault(row["family"], {"n": 0, "fired": 0, "correct": 0,
                                             "label": row["label"]})
        fam["n"] += 1
        fam["fired"] += int(row["fired"])
        fam["correct"] += int(row["correct"])
    for fam in out.values():
        fam["rate"] = fam["fired"] / fam["n"] if fam["n"] else None
    return out


def constant_rate_baseline(score: float) -> Dict[str, Any]:
    """A detector that fires on everything, or nothing.

    Reference point for reading any rate: against a corpus of 5 attacks and 5
    benign, "always fire" scores detection 1.00 and FP 1.00. An organ that only
    reports its detection rate is hiding the second number.
    """
    return {
        "always_fire": {"detection_rate": 1.0, "false_positive_rate": 1.0, "precision": 0.5},
        "never_fire": {"detection_rate": 0.0, "false_positive_rate": 0.0, "precision": None},
    }
