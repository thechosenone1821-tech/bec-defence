# Integrated into the main RAKSHA tree

This standalone Part 3 / MessageGuard snapshot was folded into the main project
on 2026-11-26. It is retained for provenance only; **do not edit code here**.

| Artifact | New source of truth |
| --- | --- |
| `messageguard/` | `../../raksha-code/citizen/messageguard/` |
| `fixtures/` | `../../raksha-code/citizen/fixtures/messageguard/` |
| `evals/` | `../../raksha-code/evals/messageguard/` |
| `EVALS.md` | `../../raksha/MESSAGEGUARD_EVALS.md` (generated) |
| `tests/test_scorer.py` | `../../raksha-code/tests/test_messageguard_v1.py` |
| `README.md` | `../../raksha-code/citizen/messageguard/README.md` and `../../specs/03_citizen_messageguard.md` |

The integrated version preserves the published 492-fixture measurement, adds
the Citizen API compatibility adapter and shared `MSG-*` i18n, and fixes two
bugs found during integration (Hindi negation word boundaries and Indic regex
boundaries). Those fixes are **not** backported to this historical snapshot.

Reproduce from `raksha-code/`:

```bash
python -m pytest tests/test_messageguard*.py -q
python evals/messageguard/run_evals.py --check
python evals/messageguard/gen_evals_md.py
```
