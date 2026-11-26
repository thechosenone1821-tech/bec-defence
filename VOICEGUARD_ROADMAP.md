# MAYA / VoiceGuard — 5-phase build roadmap

> **Last updated:** 2026-11-26 · **Version:** roadmap v1.0
> **Purpose:** split the entire VoiceGuard build into five executable phases,
> each ending in green tests and a demoable, honest increment.
> **Companion:** `MAYA_BUILD.md` (deep spec, model choice, §6 acceptance
> criteria) · `CITIZEN_APP_BUILD.md` (host app) · `INFRA_BUILD.md` (Sentinel).

---

## 0. Where the requirements come from (important)

`features.md` **does not exist** in this repository. Verified 2026-11-23 by:

- `find . -iname "features*.md"` → nothing
- `git ls-files | grep -i feature` → nothing, on every branch and every commit
- unzipping the only deleted archive in git history → nothing
- `gh api repos/…/contents/features.md` → **HTTP 404**

So the VoiceGuard feature set below is **derived from the repo docs**, which do
carry a real spec. Every feature has a citation:

| ID | Feature (VoiceGuard/Maya) | Source |
|---|---|---|
| F1 | Screen **caller audio streams** in a short rolling window | `ARCHITECTURE.md §3` ("2-second screening of caller audio streams") |
| F2 | **Spectral + anti-spoof features (LFCC/LPCC lineage)** | `ARCHITECTURE.md §3` |
| F3 | **Flag synthetic speech** (voice-clone impersonation, e.g. "digital arrest") | `ARCHITECTURE.md §3`; `CONTEXT.md §5`; `raavan/playbook.yaml` T01 |
| F4 | Powered by an **on-device distilled model** | `ARCHITECTURE.md §3` |
| F5 | **Never uploads audio** without consent; consent-gated | `ARCHITECTURE.md §3`; `CONTEXT.md §6` |
| F6 | **Ring buffer, discarded < 3 s**, visible recording indicator | `BUILD_GUIDE.md §5.5` |
| F7 | Verdict with **plain-language reasons** ("likely a synthetic voice speaking like a DSP rank officer") | `ARCHITECTURE.md §3` |
| F8 | Feeds the **Citizen Risk Engine** (voice + message + linkage → one verdict) | `ARCHITECTURE.md §3` |
| F9 | One-tap **report** into the shared graph (`CITIZEN_REPORT_VOICE`) | `ARCHITECTURE.md §3`; `api.py`; `killchain.py` T01 |
| F10 | **1930** helpline as the human next action | `ARCHITECTURE.md §3`; `api.py` |
| F11 | **Honest labelling** — never claim clone detection without a measured model | `CHANGELOG.md` v0.4.0; `EVALS.md`; `AI_HANDOFF.md §1.3` |
| F12 | **India-first**: hi/te/en, Indian-accented speech; on-device quantisation | `ROADMAP.md` Phase 2; `CONTEXT.md §6` |
| F13 | **Measured evaluation**: EER / min t-DCF / per-condition / per-language / FPR | `BUILD_GUIDE.md §6`; `EVALS.md`; `MAYA_BUILD.md §6` |

If `features.md` is supplied later, reconcile it against this table and append
the delta to `raksha/CHANGELOG.md`. Do not silently redefine a phase.

---

## 1. Current state (measured, not remembered)

```bash
cd raksha-code && pytest -q          # 67 passed
```

| | State |
|---|---|
| `citizen/voiceguard/voiceguard.py` | 66 LOC: input guards + 5 spectral features + 3 verdicts |
| Verdicts emitted today | `SILENT`, `SUSPICIOUS`, `INCONCLUSIVE` (never `LIKELY_SYNTHETIC`) |
| Engine label | `spectral_fallback_v0 (heuristic — NOT a trained anti-spoof model)` |
| Mic capture | absent — the PWA posts a **440 Hz sine wave** (`app.js::synthTone`) |
| Model | absent — no weights, no training data, no frontend |
| F1–F13 coverage | F2 partly, F3 partly (degenerate inputs only), F6 rule-not-code, F11 **yes**; the rest absent |

Honest summary: **the contract is the asset; almost everything behind it is
missing.** The plan below closes that gap in the order that keeps the demo
honest at every checkpoint.

---

## 2. The five phases

Each phase is independently shippable, ends with green tests, and **never**
removes an honesty label it has not earned the right to remove.

### Phase 1 — Trustworthy core: features, contract, verdicts, reasons
**Covers F2, F3 (deterministic part), F7 (structure), F11.** No microphone. No
ML. Pure, fast, auditable signal processing.

- Expand the feature set from 5 numbers to a real frontend-grade vector:
  LFCC-13, MFCC-13 (with deltas), spectral centroid/bandwidth/rolloff/flatness/
  flux/crest, harmonicity (HNR), pitch (F0) track + **pitch stability**, pause
  statistics (count, mean, CV), energy dynamics.
- Freeze a **contract module**: verdict enum, band table, reason codes,
  i18n keys, output schema v1 (backward compatible with today's keys).
- Every verdict carries `reasons[]` as **codes + parameters**, rendered to a
  sentence by the i18n layer (Phase 4). Never free text from the model.
- Add `features_version` so a model can be pinned to a frontend version.

**Exit criteria:** all 67 existing tests still pass unchanged; ≥ 25 new tests;
feature extraction on a 1 s clip < 5 ms; every emitted reason code has a test;
`LIKELY_SYNTHETIC` is provably never emitted (no model yet).

### Phase 2 — Capture & privacy: the ring buffer that actually exists
**Covers F1, F5, F6.** Still no ML — this phase makes the audio path real and
provably retention-free.

- `audio-capture.js` + `maya-capture.worklet.js`: 48 k → 16 k decimation,
  **3-second ring buffer, zero-filled on stop/blur/teardown**.
- Explicit user gesture to start; persistent visible indicator; hard stop.
- Consent record: what is captured, why, how long, how to stop. No audio ever
  leaves the device.
- Python reference resampler so the same clip scores identically in tests and
  in the browser.

**Exit criteria:** 16 k output within ±2 % of expected length; buffer
provably zeroed; **no** `localStorage`/`indexedDB`/`fetch` in the capture
module (grep test); indicator asserted in the DOM; Node-based tests for the
worklet logic.

### Phase 3 — Maya v1: the model pipeline (honest about its data)
**Covers F2, F3 (model part), F4, F12.** A real trained model — and a model
card that says exactly what it can and cannot do.

- Synthetic corpus generator: formant-based "human-like" speech (jitter,
  shimmer, breath noise, irregular pausing) vs "synthetic" speech (stable F0,
  regular pauses, no breath, spectral regularity).
- Frontend: LFCC + deltas, standardisation, fixed-length windowing.
- Classifier: pure-numpy logistic regression (no new dependencies), trained by
  a reproducible script; weights committed as versioned JSON.
- Calibration: temperature scaling fitted on a held-out split.
- `MODEL_CARD.md`: data provenance, generator artefacts, intended use,
  **explicit non-use**, real-world accuracy **UNMEASURED**.

**Exit criteria:** reproducible training run; held-out EER measured and
reported (on *synthetic* data — labelled as such); calibration improves
reliability; parity between training-time and inference-time frontends;
`LIKELY_SYNTHETIC` now reachable but only above a calibrated threshold.

### Phase 4 — Verdicts, reasons, multilingual, risk fusion
**Covers F7, F8, F9, F10, F12.** Turns a score into something a citizen can act
on, in their language.

- Full reason catalogue with en / hi / te renderings; no raw scores shown
  without a sentence.
- Five voice verdicts: `SILENT` · `SUSPICIOUS` · `LIKELY_SYNTHETIC` ·
  `INCONCLUSIVE` (+ `LOW_CONFIDENCE` at the risk layer).
- Citizen Risk Engine: bounded noisy-OR fusion of voice + message + campaign
  linkage, with an explicit **"I don't know"** band.
- 1930 surfaced as the primary next action on every non-trivial verdict.

**Exit criteria:** every verdict has en/hi/te strings and a test asserting key
parity; risk engine table-driven tests incl. empty input → `LOW_CONFIDENCE`;
the report rail carries the verdict + reason codes but **never** audio.

### Phase 5 — PWA integration, measurement, release
**Covers F4 (on-device), F12 (quantised), F13.** The only phase allowed to
change what the demo *claims*.

- Wire capture + model + verdicts into the Check Voice tab; remove
  `synthTone(440)` as the demo path.
- `evals/run_maya.py`: EER, per-condition (narrowband, noise SNR 5/10/20 dB,
  gain), per-language where data allows, latency p50/p95, FPR on held-out
  humans.
- Publish the table in `raksha/EVALS.md`; update `MODEL_CARD.md`; remove the
  `NOT a trained anti-spoof model` label **only** when `MAYA_BUILD.md §6` is
  fully satisfied — as its own changelog entry.

**Exit criteria:** demo works offline end-to-end; eval table reproduced in one
command; latency measured on a real device; docs and changelog updated; no
adjective where a number belongs.

---

## 3. Sequencing rules

1. **A phase may not borrow credibility from a later phase.** Phase 1 must be
   honest that there is no model; Phase 3 must be honest that the corpus is
   synthetic.
2. **Every phase ends green.** `pytest -q` is run at each gate; a red suite
   blocks the next phase.
3. **No phase removes a safety label it did not earn.** `MAYA_BUILD.md §6` is
   the single gate for calling this a clone detector.
4. **Privacy is Phase 2, not Phase 5.** Retention control must land before any
   real audio path exists.
5. **Synthetic data must be labelled synthetic**, in the model card *and* in
   `EVALS.md`, or the honesty doctrine is broken.

## 4. Phase status board

| Phase | Scope | Status | Tests added | Suite at phase end |
|---|---|---|---|---|
| 1 | Trustworthy core: features, contract, verdicts, reasons | ✅ done | 61 | 61 py |
| 2 | Capture & privacy: ring buffer, consent, indicator | ✅ done | 30 py + 24 js | 91 py · 24 js |
| 3 | Maya v1: corpus, frontend, model, calibration, card | ✅ done | 47 | 157 py |
| 4 | Verdicts, reasons, multilingual, risk fusion | ✅ done | 55 | 260 py |
| 5 | PWA integration, measurement, release | ✅ done | 38 py + 6 js | 298 py · 30 js |

**Current totals (verified 2026-11-26, after later Citizen phases and the
MessageGuard v1 integration):** `pytest -q` → **1252 passed** (1 skipped, 1
documented xfail); `node --test tests/*.test.js` → **90 passed**. **1342 passing
checks, 0 failures.** The per-phase "suite at phase end" column above is
historical and deliberately unchanged.

> This board previously listed invented counts (25/18/23/21/19 and 92→173
> "green") before any of Phase 2–5 existed. Those numbers were never produced by
> a test run and have been replaced with the counts reported by the runner. The
> lesson is recorded here rather than deleted: a status board that is filled in
> ahead of the work is a lie with a table around it.

Updated as each phase lands; the test counts are real, not aspirational.
