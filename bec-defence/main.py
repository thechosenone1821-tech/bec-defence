import numpy as np
from engines.spectral import SpectralCondensationDetector
from engines.blackhole import InformationScramblingMonitor
from sim.benchmark import run_spectral_benchmark

def main():
    rng = np.random.default_rng(42)
    d = 8
    files = 50000
    detector = SpectralCondensationDetector(safety_margin=1.2, z_alert=2.5)

    # Fit baseline on clean normal traffic — do this in production too
    detector.fit_baseline(rng.normal(0, 1, size=(files, d)))
    print(f"Baseline fitted on {files} normal sessions.\n")

    # TEST 1: normal traffic
    r1 = detector.analyze_traffic(rng.normal(0, 1, size=(500, d)))
    print("--- TEST 1: Normal human traffic ---")
    print(f"  detected={r1['attack_detected']}  lambda_max={r1['lambda_max']}  threshold={r1['mp_threshold']}")
    print(f"  suspects={len(r1['suspect_indices'])}\n")

    # TEST 2: 400 humans + 100 coordinated bots
    humans = rng.normal(0, 1, size=(400, d))
    template = rng.normal(0, 1, size=d)
    bots = template + rng.normal(0, 0.25, size=(100, d))
    r2 = detector.analyze_traffic(np.vstack([humans, bots]))
    flagged = set(r2["suspect_indices"]); truth = set(range(400, 500))
    print("--- TEST 2: Coordinated bot swarm ---")
    print(f"  detected={r2['attack_detected']}  lambda_max={r2['lambda_max']}  threshold={r2['mp_threshold']}")
    print(f"  condensation={r2['condensation_ratio']}")
    print(f"  flagged {len(flagged)}: {len(flagged & truth)} true bots (of 100), "
          f"{len(flagged - truth)} false positives (of 400)\n")

    # TEST 3: Black Hole engine
    bh = InformationScramblingMonitor(canary_patterns=("/vault/*", "*.canary"))
    print("--- TEST 3: Black Hole file monitor ---")
    print("  normal write :", bh.inspect_file_write("/data/notes.txt",
          b"Monthly hospital patient schedule and shift notes. " * 50))
    print("  ransomware   :", bh.inspect_file_write("/data/notes.txt", rng.bytes(2048)))
    print("  canary write :", bh.inspect_file_write("/vault/payroll.docx", b"hello"))

    # TEST 4: CUSUM catches a weak persistent swarm that one-shot detection mostly misses
    from engines.spectral import RollingSpectralMonitor
    roller = RollingSpectralMonitor(detector, window=500, check_every=25, drift=0.1, alarm_h=0.5)
    weak_template = rng.normal(0, 1, size=d) * 0.83       # deliberately quiet swarm
    alarms = 0
    for i in range(3000):
        if 1500 <= i < 2500 and rng.random() < 0.10:      # events 1500-2499: 10% bot traffic
            feats = weak_template + rng.normal(0, 0.25, size=d)
        else:
            feats = rng.normal(0, 1, size=d)
        a = roller.add_session(feats)
        if a:
            alarms += 1
            print(f"  CUSUM alarm #{alarms} at event {i}: lambda_max={a['lambda_max']}")
    print(f"  CUSUM alarms: {alarms}  (expect 0 before event 1500, >=1 during attack)\n")

    print("\n--- BENCHMARK (50 trials) ---")
    print(run_spectral_benchmark(detector, n_trials=50, rng=rng))

if __name__ == "__main__":
    main()