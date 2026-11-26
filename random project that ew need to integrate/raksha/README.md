# Raksha — Part 3: MessageGuard (citizen feature)

> **INTEGRATED 2026-11-26:** this standalone snapshot has been folded into the
> main `raksha/` and `raksha-code/` trees. See [INTEGRATED.md](INTEGRATED.md)
> for the new source-of-truth paths. Do not edit code here.

The detector that reads a suspicious SMS / WhatsApp message and tells the person whether it
looks like a known scam script. Deterministic, offline, explainable, multilingual
(English / Hindi / Telugu). **Deliberately rules, not a trained model** — see the
docstring in [`messageguard/scorer.py`](messageguard/scorer.py) and
[`EVALS.md`](EVALS.md) §6 for the stated cost of that choice.

## Quick start

```bash
python -c "
import messageguard as mg
print(mg.analyze('You have won Rs 25,00,000 in the KBC lucky draw. Send Rs 8,500 fee now.'))
"
python -m unittest discover tests        # 23 unit tests
python evals/run_evals.py                # recompute all EVALS.md numbers
python evals/gen_evals_md.py             # regenerate EVALS.md from results.json
```

## Layout

| Path | What it is |
| --- | --- |
| `messageguard/scorer.py` | Six weighted signal families, ×1.3 multi-family boost (cap 1.0), LOW/MODERATE/HIGH/CRITICAL bands, negation guards |
| `messageguard/tokens_en.py` / `tokens_hi.py` / `tokens_te.py` | Per-language token sets; `lang="any"` rows (shorteners, lookalike domains, apk) are language-agnostic |
| `messageguard/reasons.py` | The shared Part 1 reason-code catalogue (`MSG-*` codes, stable across languages — the only contract surface with Part 1) |
| `messageguard/bandmap.py` | Verdict → the 0.25–0.99 float the Governor's legacy organ RPC expects |
| `messageguard/normalize.py` | NFKC, casefold, zero-width strip, cheap `O T P` de-obfuscation |
| `fixtures/` | 372 hand-authored scam fixtures (120 English, 132 Hindi — 120 Devanagari + 12 Hinglish-Latin, 120 Telugu) + 120 genuine alerts, JSONL, per-message family labels |
| `evals/run_evals.py` | Computes detection rate, family recall, FPR on genuine alerts, accuracy → `evals/results.json` |
| `evals/gen_evals_md.py` | Renders `EVALS.md` from `results.json` (numbers and prose from one source) |
| `tests/test_scorer.py` | Determinism, band edges, boost, negation guard, three-script coverage, legacy band bounds |
| `EVALS.md` | Published measured accuracy: 99.2% scam detection (≥MODERATE), 11.7% FPR on genuine alerts, 96.5% overall accuracy |

## Scoring contract

```
raw     = Σ weight(fired family)          # one weight per family, however many phrases hit
score   = min(1.0, raw × 1.3 if ≥3 families fired else raw)
verdict = <0.20 LOW · <0.45 MODERATE · <0.70 HIGH · ≥0.70 CRITICAL
legacy  = to_legacy_band(verdict)          # 0.25 / 0.50 / 0.75 / 0.99 — organ RPC contract
```

Weights: credential 0.45 · authority 0.40 · money_action 0.30 · prize 0.30 · urgency 0.20 ·
link_grab 0.25. A family contributes its weight once. Every fired family produces one or more
reasons naming the family, the reason code and the matched phrase.

## Independence note

Parts 2 and 3 share **no code** beyond Part 1's reason catalogue. This directory is fully
self-contained: it can be built, tested and evaluated by two people in parallel with no
coordination beyond the `MSG-*` reason codes in `messageguard/reasons.py`. If Part 1's
canonical catalogue changes, reconcile it here and re-run the tests.

## Known failure modes (kept stated)

1. **Novel scripts** — anything outside the token sets is invisible (the corpus keeps three
   benign-looking fixtures to prove it).
2. **Legitimate urgency** — genuine bank KYC-update SMS score like phishing (measured: the
   largest FP class in `EVALS.md` §5). Fix lives in the app layer (sender-ID allowlist), not
   in more tokens.
3. **Transliteration** — Hinglish in Latin script is only partly covered.
4. **Obfuscation** — spaced `O T P` is partially mitigated; homoglyphs defeat exact tokens.
5. **No URLs fetched** — links are pattern-matched, never resolved, so the app never leaks
   that a message was checked.

## Why rules, not a model (deliberate, defended)

It runs offline on a low-end phone with no download, no GPU, no battery cost. Every hit names
the family and the matched phrase — a person can see *why* it fired, which matters more than a
few points of accuracy. It has zero training-data requirement, so it ships today. The cost —
novel-script misses and false positives on genuine urgent bank messages — is stated in the
module docstring, measured in `EVALS.md`, and accepted rather than apologised for. The optional
trained classifier stays behind the same interface and behind the corpus: order matters
(corpus first, model second), because training on hand-authored messages produces a model that
detects the author, not the scam.
