# RAKSHA — Evaluation Results

> **The rule for this file:** every number below was produced by a command in
> this repository, and every number carries the condition it was produced
> under. If a figure is not in this file, it does not go on a slide, a README
> badge, or a pitch deck.

Reproduce everything:

```bash
# from repo root — Phase 4–8 no-AI validation
python3 tools/run_phase4_pytest.py  # 196 passed; 23 model-dependent test files skipped
python3 tools/run_phase4_node_tests.py           # 60 passed; MAYA capture test skipped
python3 tools/check_phase3_contracts.py  # OK: shared contracts pinned and consistent
python3 tools/check_phase678_integration.py # OK: Phase 6-8 unified integration; no AI models loaded
python3 tools/check_phase4_citizen.py    # OK: Citizen consolidation; no AI model invoked
python3 tools/check_frozen_assets.py     # OK: 28 VoiceGuard/MAYA assets unchanged
python3 -m packages.contracts        # OK: 5 shared config pins unchanged
# from raksha-code/
python3 ../tools/run_phase4_pytest.py            # 171 passed in legacy cwd
python3 evals/messageguard/run_evals.py --check  # section 2 source JSON
python3 evals/messageguard/gen_evals_md.py       # regenerate MESSAGEGUARD_EVALS.md
# from repo root
python3 tools/check_phase5_messageguard.py # OK: one MessageGuard scorer/corpus/eval
python3 tools/check_local_links.py         # OK: local Markdown links
python3 evals/run_evals.py                      # deterministic M6 baseline × metric table
# Historical MAYA tables in section 1 are provenance only; run_maya.py was NOT run.
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

## 2. MessageGuard / Part 3 — hand-authored fixtures only

Phase 5 makes `apps/citizen/messageguard/` the one MessageGuard source; the
alternative trees are archived under `archive/provenance/`. The measurement below is generated by
`evals/messageguard/run_evals.py` from **538 hand-authored en/hi/te/hinglish fixtures**
(402 scam + 136 genuine-alert fixtures, including 46 unique Hinglish ports). It is in-distribution only; real-world
recall and false-positive rate are **UNMEASURED**. Full tables, per-family
recall and every false-positive case are in
[/raksha/MESSAGEGUARD_EVALS.md](../../../EVALS.md#messageguard).

| Metric | Value |
|---|---|
| Scam detection (verdict ≥ MODERATE) | **99.2%** (399/402) |
| False-positive rate on genuine-alert fixtures (≥ MODERATE) | **10.3%** (14/136) |
| Overall accuracy (≥ MODERATE operating point) | **96.8%** (521/538) |
| Precision at that operating point | 96.6% |
| Scam detection (score ≥ 0.70 / CRITICAL) | 55.5% |

The three missed scam fixtures are deliberately benign-like calibration rows
outside the token catalogue. The largest false-positive class is genuine-looking
bank KYC-update SMS; the documented mitigation is a sender-ID allowlist at the
app layer, not more tokens. These numbers must not be presented as field
performance.

---

## 3. Test inventory

| suite | result | covers |
|---|---|---|
| Python (`tools/run_phase4_pytest.py`, repo root) | **196 passed**, 0 failed, 4 warnings | deterministic spine/Sentinel/PWA/MessageGuard/Phase 2/3/4/5 checks; no AI model modules loaded |
| Python (`../tools/run_phase4_pytest.py`, `raksha-code/`) | **171 passed**, 0 failed, 4 warnings | legacy-cwd deterministic subset; no root-only layout/Phase 4/5 tests |
| Browser (`tools/run_phase4_node_tests.py`) | **60 passed** | panic, family mode, offline queue, spine delivery; frozen MAYA capture JS test skipped |
| Contract / frozen-asset / eval / Phase-5/6-8 checks | **green** | `tools/check_phase3_contracts.py`, `tools/check_phase4_citizen.py`, `tools/check_frozen_assets.py`, `tools/check_phase5_messageguard.py`, `tools/check_phase678_integration.py`, `tools/check_local_links.py`, `python -m packages.contracts`, MessageGuard `--check` |
| Compile / links / imports / help | **clean** | `compileall`, 336/336 local links, no-model import smoke, 5 model-free entrypoint helps, `git diff --check` |
| **Total passing checks** | **256** | 196 Python root + 60 Node; 0 failures. Legacy cwd is a subset, not double-counted. Phase 5 checker and link checker are deterministic commands, not extra pytest/Node checks |

Phase 6–8 adds 10 deterministic unified-integration tests and one checker; Phase 4 adds 13 deterministic Citizen consolidation tests (7 root + 6
legacy-cwd) and introduces an explicit no-AI test policy:
`tools/run_phase4_pytest.py` skips 23 model-dependent Python test files and
`tools/run_phase4_node_tests.py` skips one frozen MAYA capture Node test file.
`tools/phase4_no_ai_plugin.py` fails pytest if any VoiceGuard/MAYA/SLM/Commander
module loads. The exact skip list and rationale are in
[`/raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md) and
[`/BUILD_STATE.md`](../../../docs/STATUS.md). Phase 5 adds 12 deterministic
single-source MessageGuard tests (6 root + 6 legacy-cwd), two archived
provenance test-dir ignores, `tools/check_phase5_messageguard.py` and
`tools/check_local_links.py`; see
[`/raksha/PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](../../../raksha/PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md).
Older full-suite counts remain historical snapshots in their phase reports.

---

## 4. Bugs the MAYA evaluation phase caught


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


---

## 5. Bugs the MessageGuard integration caught

| # | Bug | Symptom | Fix |
|---|---|---|---|
| 1 | Hindi negation cue matched inside a non-negated word | bare `न करें` matched the tail of `सत्यापन करें` and suppressed a real UPI-PIN request | Require whitespace/punctuation around negation cues; add a regression test |
| 2 | ASCII `\b` boundaries fail after Indic combining marks | Telugu `UPI పిన్ ఇవ్వండి` and `kyc ధృవీకరణ చేసి` compatibility rows never matched | Use script-safe regex boundaries and add en/hi/te integration tests |

Neither fix changed the published en/hi/te per-language aggregates; Phase 5 regenerated the overall 538-fixture headline numbers;
`python evals/messageguard/run_evals.py --check` and the integration test
assert that the committed results still reproduce exactly.
