# spectral-defence-poc

Research-inspired detection prototype. Two detector engines (spectral
coordination detection and an entropy + contextual file-write monitor) plus
a minimal identity registry, dry-run response layer and filesystem watcher.

This is **not** production security software. Identity, enforcement and
recovery capabilities described in the larger system vision are **planned**,
not implemented. See "Limitations" below.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ is required. Tested on CPython 3.11.

## Run the demo

```bash
python main.py
```

The demo prints seven sections: normal traffic, coordinated swarm, rolling
CUSUM, direct file-monitor calls, a real filesystem watcher on a temp
sandbox directory, correlation + dry-run response (including a demo
revocation against the in-memory registry), and a seeded scenario-matrix
benchmark. An append-only JSONL audit log is written to a temp file whose
path is printed at the end.

## Run the tests

```bash
pytest -q
```

Each test names the defect it pins down from the source review.

## Run only the benchmark

```python
from sim.benchmark import run_scenario_matrix, summarize_matrix
from engines.spectral import SpectralCondensationDetector, MeanShiftBaseline, DistanceBaseline

mat = run_scenario_matrix(
    detectors={
        "spectral": SpectralCondensationDetector(),
        "mean_shift": MeanShiftBaseline(),
        "distance": DistanceBaseline(),
    },
    n_seeds=3,
)
print(summarize_matrix(mat))
```

## Repository layout

```
engines/     spectral + blackhole detectors
sim/         seeded scenario-matrix benchmark
core/        unified event format, JSONL audit log, correlation
identity/    minimal identity registry (declared identities only)
response/    dry-run response layer (only in-memory revocation is enforced)
watch/       filesystem watcher on one sandbox directory
tests/       pytest regression tests
main.py      integrated demo
```

## Limitations

- **Synthetic evaluation only.** Benchmark numbers come from seeded
  synthetic data, not real traffic. Do not cite them as evidence of
  real-world protection.
- **No process attribution.** The filesystem watcher identifies files and
  events but not the writing process. ``actor`` is always ``"unknown"``.
- **No real human verification.** A credential establishes a registered
  identity, not proof that its operator is human. ``kind`` is a declared
  attribute set at registration time, not inferred from the credential.
- **Dry-run responses only.** No process killing, no real file encryption,
  no real user lockout. The only enforced action is revocation against the
  in-memory demo registry.
- **MP edge is a heuristic null.** Per-feature standardisation does not
  remove normal correlations between features. Calibrate
  ``calibrate_empirical_edge`` on held-out benign windows that include
  correlated benign workloads before trusting thresholds.
- **Overlapping rolling windows.** Successive ``lambda_max`` samples from
  ``RollingSpectralMonitor`` are not independent; thresholds calibrated on
  independent windows will be conservative (more alarms, not fewer).
- **Planned, not implemented:** OAHIS identity protocol, synthetic
  honey-tensors, unified threat intelligence layer, real file protection /
  integrity monitoring / backup recovery, automatic process termination,
  production key management.

## License

MIT. See `LICENSE`.
