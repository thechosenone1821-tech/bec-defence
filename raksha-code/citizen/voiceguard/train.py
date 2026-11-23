"""MAYA / VoiceGuard — reproducible training run (Phase 3).

    python -m citizen.voiceguard.train            # train + save + print table
    python -m citizen.voiceguard.train --dry-run  # measure without writing

Determinism contract: same seed + same code ⇒ byte-identical artefact. If a
run produces different weights, something changed that was not supposed to
(the frontend, the corpus, or the hyperparameters) — treat it as a bug.

The printed table is the *only* source of the numbers that may appear in
``raksha/EVALS.md``. Every figure is labelled SYNTHETIC CORPUS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any, Dict

import numpy as np

from . import corpus, model as M


def run(seed: int = 20260101, n_per_class: int = 60,
        l2: float = 1.0, save: bool = True) -> Dict[str, Any]:
    data = corpus.build(seed=seed, n_per_class=n_per_class)

    Xtr = M.design_matrix(data["train"]["clips"])
    ytr = data["train"]["labels"]
    Xva = M.design_matrix(data["val"]["clips"])
    yva = data["val"]["labels"]
    Xte = M.design_matrix(data["test"]["clips"])
    yte = data["test"]["labels"]

    params = M.train(Xtr, ytr, l2=l2)

    # Calibrate on the val split (never the test split).
    uncal = M.MayaModel({**params, "temperature": 1.0})
    va_rows = M.design_matrix(data["val"]["clips"])
    va_probs = np.asarray([uncal.probability_from_row(r) for r in va_rows])
    params["temperature"] = M.fit_temperature(va_probs, yva)

    # Then pick the decision threshold from the same held-out split, under a
    # false-positive ceiling: missing a clone is better than accusing a person.
    calibrated = M.MayaModel(params)
    va_cal = np.asarray([calibrated.probability_from_row(r) for r in va_rows])
    params["decision_threshold"] = M.choose_threshold(va_cal, yva, target_fpr=0.05)

    fitted = M.MayaModel(params)
    train_metrics = M.evaluate(fitted, data["train"]["clips"], ytr)
    val_metrics = M.evaluate(fitted, data["val"]["clips"], yva)
    test_metrics = M.evaluate(fitted, data["test"]["clips"], yte)

    # Sensitivity: does the model survive a small amount of noise the corpus
    # does not have? A model that only works on pristine synthesis is fragile.
    rng = np.random.default_rng(seed + 7)
    noisy = [c + rng.normal(0, 0.02, c.size).astype(np.float32)
             for c in data["test"]["clips"]]
    noisy_metrics = M.evaluate(fitted, noisy, yte)

    # Two different digests, and confusing them is a real trap:
    #
    #   params_sha256_16 -- digest of the parameters. Stored *inside* the file,
    #                       because it is reproducible from training alone and
    #                       therefore identifies the *fit*.
    #   file_sha256_16   -- digest of the bytes on disk. Cannot be stored in the
    #                       file it hashes (chicken-and-egg), so it is computed
    #                       after writing and returned for the caller to pin.
    #
    # The earlier single field was called "artefact_sha256" but held the params
    # digest, so it never matched `sha256sum` on the file — and the test that
    # pinned it was therefore checking the wrong thing.
    params_digest = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
    params["training"] = {
        "seed": seed,
        "n_per_class": n_per_class,
        "l2": l2,
        "corpus": "SYNTHETIC (procedural) — see MODEL_CARD.md",
        "measured_on_real_speech": False,
        "params_sha256_16": params_digest,
    }

    file_digest = None
    if save:
        path = M.save(params)
        # The digest of the bytes actually written. This is the identifier to
        # pin in tests and to quote in EVALS.md / MODEL_CARD.md.
        with open(path, "rb") as fh:
            file_digest = hashlib.sha256(fh.read()).hexdigest()[:16]

    return {
        "params": params,
        "params_sha256_16": params_digest,
        "file_sha256_16": file_digest,
        "temperature": params["temperature"],
        "train": train_metrics,
        "val": val_metrics,
        "test": test_metrics,
        "test_noisy": noisy_metrics,
    }


def _row(name: str, m: Dict[str, Any]) -> str:
    return (f"| {name} | {m['n']} | {m['eer']} | {m['accuracy_at_threshold']} "
            f"| {m['precision']} | {m['recall']} | {m['false_positive_rate']} |")


def main() -> None:
    ap = argparse.ArgumentParser(description="Train Maya voiceguard model")
    ap.add_argument("--seed", type=int, default=20260101)
    ap.add_argument("--n-per-class", type=int, default=60)
    ap.add_argument("--l2", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out = run(seed=args.seed, n_per_class=args.n_per_class, l2=args.l2,
              save=not args.dry_run)

    print("MAYA model — SYNTHETIC CORPUS ONLY. Not a real-world accuracy claim.")
    print()
    print("| split | n | EER | acc@0.80 | precision | recall | FPR |")
    print("|---|---|---|---|---|---|---|")
    print(_row("train", out["train"]))
    print(_row("val (calibration)", out["val"]))
    print(_row("test (held out)", out["test"]))
    print(_row("test + noise", out["test_noisy"]))
    print()
    print(f"temperature: {out['temperature']}")
    print(f"params sha256[0:16] : {out['params_sha256_16']}")
    print(f"file   sha256[0:16] : {out.get('file_sha256_16', '(dry-run)')}")
    if args.dry_run:
        print("(dry run — weights not written)")


if __name__ == "__main__":
    main()
