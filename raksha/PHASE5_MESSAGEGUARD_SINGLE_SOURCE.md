> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../docs/STATUS.md); see the [retired code note](../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# Phase 5 — Make MessageGuard single-source

> **Status:** implemented on `arena/3b136fd9-bec-defence` · **Date:** 2026-11-26
> **Scope:** Phase 5 only. No Phase 6+ work, no app-root merge, no
> VoiceGuard/MAYA integration, no AI model inference, no commit or push.

## Goal

Remove the last duplicate Citizen detector. Phase 4 left one Citizen service
and one physical PWA shell, but MessageGuard still had an integrated v1
runtime plus an independent Part 3 package and a standalone snapshot. Phase 5
makes `apps/citizen/messageguard/` the one detector and archives the rest as
provenance. The maintainer's standing **no AI models** rule was preserved:
no LLM, Commander, SLM/Ollama, MAYA or VoiceGuard model endpoint, no model
inference, and no model-dependent test file was run.

## What changed

### One detector interface

`apps/citizen/messageguard/` remains the canonical scorer. Its public interface
now also owns:

- `SUPPORTED_LANGS = ("auto", "en", "hi", "te", "hinglish")`;
- `detect_language()` — deterministic script/cue matching hint;
- `legacy_organ.py` — the ported 0.25–0.99 legacy organ adapter built from the
  canonical result dictionary, with `band` and `clamp` modes;
- `__main__.py` — a sanitized operator CLI with `--lang`, `--json`, `--legacy`
  and `--citizen-lang`.

`analyze(..., lang="auto")` still applies en/hi/te plus language-agnostic rows,
exactly preserving the published en/hi/te measurement. `lang="hinglish"` adds
the dedicated Latin-Hindi rows plus language-agnostic rows. `score_message()`
is still the Citizen API compatibility adapter. `citizen.messageguard` and
`raksha-code/apps/citizen/messageguard` resolve to the same canonical package;
they are aliases, not a second implementation. The independent `assess()` /
`SignalFamilyScorer` scorer was not ported.

### One corpus

`raksha-code/citizen/fixtures/messageguard/` is the only active corpus. It now
has **538 hand-authored / in-distribution fixtures**:

| Label | en | hi | te | hinglish | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scam | 120 | 132 | 120 | 30 | **402** |
| Genuine / benign | 40 | 40 | 40 | 16 | **136** |
| Total | 160 | 172 | 160 | 46 | **538** |

The 46 Hinglish rows (30 scam, 16 benign) are the unique valuable rows ported
from the alternative Part 3 corpus; every normalized text differs from the
earlier 492 fixtures and every ported row carries a `source` provenance field.
The other 385 alternative en/hi/te rows were deliberately **not** ported: they
duplicate canonical language coverage and would add known false positives
without a new measured condition. The corpus README states the hand-authored,
no-PII, no-field-claim scope.

### One generated eval document and one reason catalogue

`raksha-code/evals/messageguard/run_evals.py` is the one MessageGuard eval
runner. `results.json` and `raksha/MESSAGEGUARD_EVALS.md` are regenerated from
the one corpus and one scorer. en/hi/te rows use `lang="auto"`; Hinglish rows
use `lang="hinglish"`. The generated document explicitly says every number is
**hand-authored / in-distribution** and that real-world recall/FPR remain
**UNMEASURED**.

Current single-source headline numbers from the regenerated JSON:

| Metric | Value |
| --- | --- |
| Scam detection (≥ MODERATE) | **99.2%** (399/402) |
| False-positive rate on genuine-alert fixtures (≥ MODERATE) | **10.3%** (14/136) |
| Overall accuracy (≥ MODERATE) | **96.8%** |
| Precision at that operating point | 96.6% |
| Score ≥ 0.70 / CRITICAL detection | 55.5% |
| Family recall | 100% in-distribution on labelled families |

The en/hi/te per-language aggregates are byte-for-byte unchanged from the
pre-Phase-5 `results.json`; only the corpus totals and overall aggregates
change because 46 unique Hinglish rows were added. All 30 ported Hinglish scam
rows are detected at ≥MODERATE and all 16 ported Hinglish benign rows stay LOW.
The three scam misses remain the deliberately benign-like en/hi/te calibration
fixtures.

`packages/contracts/reasons.py` remains the one `MSG-*` catalogue. The new
Hinglish token rows reuse existing codes; no `msg.*` catalogue was ported.
`apps/citizen/copy.py` and `packages/contracts/i18n.py` still render citizen
sentences from that one catalogue, with no raw score, no `SAFE` verdict and no
matched scam phrases in the explanation layer.

### Provenance archive

The two historical trees were moved with `git mv` into `archive/provenance/`:

| Original | Archived as |
| --- | --- |
| `raksha-messageguard/raksha/` | `archive/provenance/messageguard-alternative/raksha/` |
| `random project that ew need to integrate/raksha/` | `archive/provenance/messageguard-snapshot/raksha/` |

`archive/provenance/README.md` plus one `PROVENANCE.md` per tree records what
was ported, what was not, and why. The archived Python package directories
were renamed from `messageguard` to `messageguard_legacy` so
`raksha.messageguard` cannot be imported from a repository root. The archived
test directories are ignored by `archive/provenance/conftest.py` and by
`tools/run_phase4_pytest.py`; they are historical evidence, not a second
pytest suite. Internal historical imports are intentionally not repaired.

## Safety and honesty rails

- No AI model, VoiceGuard/MAYA inference, Commander/SLM endpoint or network
  call was used; VoiceGuard/MAYA frozen assets remain untouched.
- No raw score is shown to a citizen; the operator CLI and legacy organ payload
  are explicitly not citizen UI and contain no matched phrases.
- No `SAFE` verdict, no PII forwarding, no clone/field/real-network claim, and
  no weakened signature/Governor requirement.
- Published numbers are in-distribution only; real-world recall/FPR remain
  UNMEASURED.
- No commit or push was performed.

## Verification

Deterministic, model-free checks:

```bash
python tools/check_phase5_messageguard.py
python tools/check_local_links.py
python tools/check_phase4_citizen.py
python tools/check_phase3_contracts.py
python -m packages.contracts
python tools/check_frozen_assets.py
(cd raksha-code && python evals/messageguard/run_evals.py --check)
python tools/run_phase4_pytest.py
(cd raksha-code && python ../tools/run_phase4_pytest.py)
python tools/run_phase4_node_tests.py
```

`tools/check_phase5_messageguard.py` proves one importable scorer, one
`MSG-*` catalogue, one 538-row corpus, one `results.json`, one generated eval
document, the archived provenance markers, plain (not backslash-escaped) lang
quotes and a citizen-safe CLI. It also verifies that the generated document is
exactly what `gen_evals_md.py` would write and calls
`tools/check_local_links.py` for every local Markdown link. The no-AI pytest runner skips the same 23 model-dependent Python test
files and one frozen MAYA capture Node test as Phase 4, and additionally
ignores the two archived provenance test directories.

Current deterministic suite counts are kept in `BUILD_STATE.md` and
`raksha/EVALS.md`; this report does not duplicate a number that can drift.
Exit gate: pytest finds one MessageGuard suite, no second scorer is importable,
one `run_evals.py --check` reproduces the published numbers, and all published
numbers remain explicitly hand-authored / in-distribution. See
[`adr/ADR-013-messageguard-single-source.md`](adr/ADR-013-messageguard-single-source.md).
