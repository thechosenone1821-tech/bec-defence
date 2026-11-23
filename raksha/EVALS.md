# RAKSHA — Evaluation Results

> **The rule for this file:** every number below was produced by a command in
> this repository, and every number carries the condition it was produced
> under. If a figure is not in this file, it does not go on a slide, a README
> badge, or a pitch deck.

Reproduce everything:

```bash
cd raksha-code
python3 -m pytest tests/ -q          # 298 passed
node --test tests/maya_capture.test.js   # 30 passed
python3 evals/run_maya.py            # the tables below
```

---

## 1. MAYA / VoiceGuard — synthetic corpus only

| Field | Value |
|---|---|
| Model | `maya-lr-v1` (numpy logistic regression, 2 features) |
| Artefact | `citizen/voiceguard/maya_lr_v1.json`, 734 bytes |
| File SHA-256 (first 16) | `8b140095e5f8599e` (verify: `sha256sum citizen/voiceguard/maya_lr_v1.json`) |
| Params SHA-256 (first 16) | `423a58f49368e340` (stored in the file; identifies the fit) |
| Equation | `P(spoof) = σ((−0.115 − 0.963·z(pause_cv) − 0.873·z(f0_cv)) / 0.25)` |
| Decision threshold | `0.9412` (chosen for ≤ 5 % FPR on the val split) |
| Features | `pause_cv` (pause-length variation), `f0_cv` (pitch variation) |
| Training data | **procedural synthetic corpus**, `seed=20260101`, 120 clips |

### 1.1 Headline — held-out test split

| split | n | EER | accuracy | precision | recall | FPR |
|---|---|---|---|---|---|---|
| train | 108 | 0.287 | 76.8 % | 88.9 % | 60.4 % | 7.3 % |
| val (calibration) | 36 | 0.167 | 83.3 % | 100.0 % | 68.4 % | 0.0 % |
| **test (held out)** | **36** | **0.167** | **86.1 %** | **100.0 %** | **72.2 %** | **0.0 %** |

n = 36 means the 95 % confidence interval on accuracy is roughly ±11
percentage points. These figures support the claim *"it works on its own
corpus"* and nothing stronger.

### 1.2 Robustness by condition — the table that matters

A single accuracy number hides the fact that real calls are degraded. Each row
applies one condition to the same held-out clips:

| condition | n | EER | accuracy | recall | FPR |
|---|---|---|---|---|---|
| clean | 36 | 0.167 | 86.1 % | 72.2 % | 0.0 % |
| **narrowband (telephony, 300–3400 Hz)** | 36 | **0.278** | **69.4 %** | **38.9 %** | 0.0 % |
| μ-law 8-bit companding | 36 | 0.167 | 86.1 % | 72.2 % | 0.0 % |
| packet loss 2 % | 36 | 0.222 | 80.6 % | 61.1 % | 0.0 % |
| additive noise σ=0.02 | 36 | 0.167 | 86.1 % | 72.2 % | 0.0 % |
| gain ×0.3 | 36 | 0.167 | 86.1 % | 72.2 % | 0.0 % |

**Reading this honestly:** band-limiting to the telephone passband roughly
halves recall (72 % → 39 %), because the cue that survives best here lives
partly in the high band. That is the expected failure mode of a two-feature
model, and it is the single most important number on this page for anyone
considering a real deployment. Gain and μ-law are handled correctly — a
normalisation bug that made the app volume-dependent would show up here as a
collapse, and does not.

### 1.3 Citizen-facing behaviour

| class | verdicts | false accusation rate |
|---|---|---|
| synthetic (n=18) | 13 `LIKELY_SYNTHETIC`, 5 `INCONCLUSIVE` | — |
| bona-fide (n=18) | 18 `INCONCLUSIVE` | **0.0 %** |

The false-accusation rate is the number that decides whether anyone keeps the
app installed. On this corpus it is zero, and it is zero *because* the
threshold was chosen against an FPR ceiling rather than for maximum accuracy.

### 1.4 Latency

| metric | value |
|---|---|
| p50 | 16.6 ms |
| p95 | 17.1 ms |
| max | 17.2 ms |

**Sandbox laptop wall-clock, not a phone.** No mobile measurement exists. Any
SLO claim based on this number would be invented.

### 1.5 What this model does **not** do

- It has **never seen real recorded speech**. `MEASURED_ON_REAL_SPEECH = False`.
- It has **never seen a neural voice clone** (no TTS, TTS-clone or voice
  conversion system is in the corpus).
- It has **no phonetic model**, so it cannot claim anything about Indian
  languages or accents. The generator produces no speech, only synthetic
  surrogates with controllable statistics.
- `may_claim_clone_detection()` returns **False**. The engine string says
  "trained on SYNTHETIC corpus — real-world accuracy UNMEASURED; NOT a
  validated anti-spoof model" and that string is served in the API payload.

**Honest summary:** this is a working, tested, calibrated pipeline with a
measured *synthetic* baseline and a demonstrated degradation curve. It is not
an anti-spoof product, and the code refuses to describe itself as one.

---

## 2. Test inventory

| suite | count | covers |
|---|---|---|
| `test_maya_phase1.py` | 61 | features, contract, verdicts, determinism, honesty gate |
| `test_maya_phase2.py` | 30 | ring buffer, consent, retention, Python/JS parity |
| `test_maya_phase3.py` | 47 | corpus, model, calibration, artefact integrity, honesty |
| `test_maya_phase4.py` | 55 | reason catalogue, en/hi/te, risk fusion, API |
| `test_maya_phase5.py` | 38 | threshold search, degradation, release claims, e2e |
| `test_voiceguard.py`, `test_citizen_api.py`, others | 67 | pre-existing platform tests |
| **pytest total** | **298** | |
| `maya_capture.test.js` | 30 | browser capture, worklet, decimation, page wiring, band accessibility |
| **grand total** | **328** | 0 failures |

---

## 3. Bugs this evaluation phase caught

Recorded because each one was invisible to the metric that was being reported.

| # | Bug | Symptom | Fix |
|---|---|---|---|
| 1 | Silence scored as `LIKELY_SYNTHETIC` | The app said "this is probably an AI-generated voice" about a recording containing no voice (P(spoof)=0.94 on digital zero) | Gate the model behind an eligibility check; SILENT/INCONCLUSIVE never consult it |
| 2 | Two probability paths | `evaluate()` used the calibrated path, `score_voice` the raw one. The table said 78 % recall; the app demonstrated 11 % | One public calibrated path; raw path renamed private-by-convention |
| 3 | `choose_threshold` returned the *least* sensitive threshold | Recall 77.8 % → 5.6 %, while reported EER stayed at 0.167 | Iterate low→high and stop at the first threshold inside the FPR ceiling |
| 4 | NaN in JSON request → HTTP 500 | A malformed client request could take the endpoint down | Sanitise samples at the API boundary |
| 5 | Corpus artefacts drove "accuracy" | Perfect EER came from pause *duty cycle* and pause *depth*, not voice quality | Match both classes; documented in `MODEL_CARD.md` |
| 6 | Spectral cues learned the channel, not the speaker | EER 0.000 clean, 0.667 under noise | Feature selection measured under noise; spectral keys banned from the model |
| 7 | **Served page could not load its own assets** | `/` returned index.html but every relative asset 404'd — unstyled page, no scripts, so the mic path always reported "microphone not available" | Redirect `/` → `/app/`; test now resolves assets *from the landing URL* |
| 8 | Artefact hash was the params digest, mislabelled | Pinned SHA never matched `sha256sum` on the file, so the integrity test checked the wrong thing | Split into `params_sha256_16` (in file) and file digest (recomputed from disk, pinned in tests) |

Bug 3 is the instructive one: the accuracy metric and the citizen's actual
experience disagreed, and only a test that compared the two caught it.
