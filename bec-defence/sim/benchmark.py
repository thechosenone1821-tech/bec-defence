import numpy as np

def run_spectral_benchmark(detector, n_trials=50, n_humans=400, n_bots=100,
                           d=8, jitter=0.25, seed=0, rng=None):
    rng = rng or np.random.default_rng(seed)
    tp = fp = fn = 0
    detected_batches = 0

    for _ in range(n_trials):
        humans = rng.normal(0, 1, size=(n_humans, d))
        template = rng.normal(0, 1, size=d)          # new bot script each trial
        bots = template + rng.normal(0, jitter, size=(n_bots, d))
        res = detector.analyze_traffic(np.vstack([humans, bots]))

        detected_batches += res["attack_detected"]
        flagged = set(res["suspect_indices"])
        truth = set(range(n_humans, n_humans + n_bots))
        tp += len(flagged & truth)
        fn += len(truth - flagged)
        fp += len(flagged - truth)

    return {
        "batch_detection_rate": round(detected_batches / n_trials, 3),
        "precision": round(tp / max(tp + fp, 1), 3),
        "recall": round(tp / max(tp + fn, 1), 3),
        "false_positive_rate": round(fp / max(n_humans * n_trials, 1), 4),
    }