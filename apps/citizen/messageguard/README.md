# MessageGuard v1 (integrated)

This package is the standalone Part 3 MessageGuard work folded into the main
Citizen app. It is deterministic, stdlib-only, offline, and explainable. It is
**not** a trained classifier; all counts below are hand-authored /
in-distribution fixture counts, real-world recall and FPR are UNMEASURED.

| File | Role |
| --- | --- |
| `scorer.py` | Six weighted signal families, negation guards, band edges, and the `score_message()` API adapter |
| `tokens_en.py` / `tokens_hi.py` / `tokens_te.py` | English, Hindi and Telugu regex catalogues plus language-agnostic link tokens |
| `reasons.py` | Stable `MSG-*` reason catalogue shared with the citizen explanation layer |
| `normalize.py` | NFKC, casefold, zero-width stripping, acronym de-obfuscation |
| `bandmap.py` | Verdict → 0.25–0.99 legacy organ RPC band |
| `../fixtures/messageguard/` | 402 scam + 136 genuine hand-authored JSONL fixtures with language and family labels, including 46 Hinglish ports |
| [`../../../evals/`](../../../evals/) | One reproducible measurement runner and generated results |
| [`../../../EVALS.md`](../../../EVALS.md) | Published, generated evaluation |

The older 20-message `../fixtures/message_fixtures.json` remains as a smoke
corpus: the integrated scorer passes it 20/20, but no accuracy claim is made
from it. The published numbers come from the 538-message corpus only.

Reproduce from `raksha-code/`:

```bash
python -m evals.run_evals --check
make eval-generate
```

The API keeps `lang="auto"` for detection even when the caller asks for Hindi
or Telugu explanations: the request language selects citizen copy, not the
language a scam message may be written in.
