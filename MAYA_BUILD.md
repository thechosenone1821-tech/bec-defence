# MAYA — the VoiceGuard build spec (what is built, what to build, how to build it)

> **Last updated:** 2026-11-26 · **Owner of record:** repo maintainer (human)
> **Parked by Phase 1:** VoiceGuard / MAYA is a frozen seam, not part of the
> combined-system 10 phases. See
> [`raksha/adr/ADR-009-voiceguard-frozen-seam.md`](raksha/adr/ADR-009-voiceguard-frozen-seam.md)
> and [`raksha-code/citizen/voiceguard/FROZEN.md`](raksha-code/citizen/voiceguard/FROZEN.md).
> **What Maya is:** the citizen-facing **voice-clone / synthetic-speech screen**
> in RAKSHA Citizen — the module currently implemented as
> `raksha-code/citizen/voiceguard/` (`score_voice()`), surfaced in the PWA's
> **Check Voice** tab and in `POST /api/citizen/screen_voice`.
> **Name status:** *"Maya"* is a maintainer-assigned product name used in
> historical VoiceGuard docs; it is not a combined-system app name. This spec is
> retained as context, not as a Phase 1–10 integration deliverable.
> **Evidence base:** `citizen/voiceguard/voiceguard.py` (66 LOC),
> `citizen/api.py`, `citizen/app/{app.js,index.html}`,
> `tests/test_voiceguard.py` (6 tests), `raksha/ARCHITECTURE.md §3`,
> `raksha/BUILD_GUIDE.md §5.5`, `raksha/ROADMAP.md` Phase 2.
> **Companion docs:** `CITIZEN_APP_BUILD.md` (host app) · `INFRA_BUILD.md` (Sentinel).

**Status vocabulary:** `BUILT` · `PARTIAL` · `STUB` (labelled) · `ABSENT`.

---

## 1. The one paragraph everyone must read first

Maya today is **not a voice-clone detector.** It is a contract plus a
deterministic spectral fallback that can flag *degenerate* audio — silence, a
pure tone, near-white noise — and returns `INCONCLUSIVE` for real speech. The
engine string it emits says, in the payload:
`"spectral_fallback_v0 (heuristic — NOT a trained anti-spoof model)"`, and the
module docstring says it "CANNOT detect modern neural voice clones."

That honesty is correct and must be preserved until a trained model is actually
measured. **The demo currently posts a 440 Hz sine wave** — `synthTone(440)` in
`citizen/app/app.js` — and the fallback flags it `SUSPICIOUS`. That proves the
plumbing, not the defence. Nobody may claim "we detect AI voice clones" until
§6 is filled with measured numbers.

---

## 2. Verified built state

| # | Capability | Status | Evidence | Honest limit |
|---|---|---|---|---|
| M-01 | `score_voice(samples) → {verdict, score, engine, reason, features}` contract | BUILT | `voiceguard/voiceguard.py`; `tests/test_voiceguard.py` | Contract is the asset — keep it stable across every model swap |
| M-02 | Input hardening: < 512 samples, non-finite, `|x| > 4.0` ⇒ `INCONCLUSIVE` | BUILT | same file; 3 dedicated tests | Never returns a confident verdict on garbage — correct fail-closed behaviour |
| M-03 | Spectral features: RMS, ZCR, spectral centroid, flatness, crest factor | BUILT | `_features()` (Hann window, `rfft`, geometric/arithmetic mean ratio) | Descriptive only; no discriminative power against modern TTS |
| M-04 | Verdict rules: `SILENT` / `SUSPICIOUS` (pure-tone, near-white) / `INCONCLUSIVE` | BUILT | `rms<1e-4`; `flatness<0.02 and crest<3.5`; `flatness>0.85` | **Real human speech and a good neural clone both land in `INCONCLUSIVE`** |
| M-05 | Determinism (same input ⇒ same output) | BUILT | `test_deterministic` | — |
| M-06 | Honesty labelling in payload + UI | BUILT | engine string; `index.html` voice tab copy ("heuristic fallback", "NOT a trained anti-spoof model") | Must survive every future refactor — add a test that greps for the label |
| M-07 | API endpoint with size cap | BUILT | `POST /api/citizen/screen_voice`, `MAX_SAMPLES = 240 000` (15 s @ 16 kHz), 413 on oversize | JSON float array on the wire: ~4 MB for 15 s — unusable on a village connection, see M-12 |
| M-08 | Microphone capture | **ABSENT** | `app.js::synthTone()` only | Maya has never heard a real voice |
| M-09 | Trained anti-spoof model | **ABSENT** | `ARCHITECTURE.md §3` says "on-device distilled model"; `ROADMAP.md` Phase 2 "on-device model quantization v1"; `BUILD_GUIDE.md` M3 says "pretrained model via ONNX if available, deterministic spectral fallback otherwise" | No model, no weights, no training data, no eval set |
| M-10 | On-device inference | **ABSENT** | all scoring is server-side Python | Audio would leave the phone today — violates `CONTEXT.md §6` |
| M-11 | Live call screening (2-second rolling window during a call) | **ABSENT** | `ARCHITECTURE.md §3` ("2-second screening of caller audio streams") | PWA cannot tap call audio; needs the native wrapper (see M-15) |
| M-12 | Consent + zero-retention enforcement | PARTIAL | `BUILD_GUIDE.md §5.5` (ring buffer, visible indicator, < 3 s discard) is a *rule*, not implemented code | Nothing enforces it yet |
| M-13 | Multilingual / Indian-accent evaluation | **ABSENT** | — | The hardest and most differentiating work in this whole project; see §6 |
| M-14 | Score calibration (probabilities, not vibes) | **ABSENT** | `score` is a hand-picked 0.9/0.5/0.3/0.0 | Cannot be aggregated by the Risk Engine without calibration |
| M-15 | Family-mode escalation for voice verdicts | **ABSENT** | `CITIZEN_APP_BUILD.md` C-10 | — |

---

## 3. Design constraints that are not negotiable

Derived from `ARCHITECTURE.md §3`, `BUILD_GUIDE.md §5`, `CONTEXT.md §6`:

1. **Audio never leaves the device.** Inference runs in the browser/app. A
   server round-trip of raw audio is a privacy regression even if the server is
   ours.
2. **Rolling buffer only.** ≤ 3 s retained, zeroed on stop, visible indicator
   whenever the mic is live.
3. **Fail to `INCONCLUSIVE`, never to `SAFE`.** A miss is bad; a false "this
   caller is genuine" is worse.
4. **Never accuse a person.** Verdicts are advisory and always name a human
   next action (hang up / call back on an official number / 1930).
5. **Works offline, on a mid-range Android, with no Play Services.**
   `onnxruntime-web` (WASM) by default.
6. **One contract.** `score_voice()`'s shape is frozen; models are swappable
   behind it. Anything that changes the shape is a contract version bump.
7. **Labels are part of the product.** If the model is not trained/measured,
   the payload must say so. Enforce with a test.

---

## 4. Target architecture

```text
┌─ Android / PWA ────────────────────────────────────────────────┐
│  getUserMedia ──▶ AudioWorklet (48k→16k, ring 3 s, zero-fill)   │
│                          │                                      │
│                          ▼                                      │
│  maya-web.js  ──▶  Frontend (features, ~10 ms)                  │
│       │                │ log-mel / LFCC / CQCC + Δ, 1.5 s window│
│       │                ▼                                        │
│       │        ONNX INT8 anti-spoof model (AASIST-class)        │
│       │                │ score σ ∈ [0,1]                        │
│       │                ▼                                        │
│       │        Calibrator (per-codec isotonic/temperature)      │
│       │                │ p(clone)                               │
│       ▼                ▼                                        │
│  Decision: SILENT | SUSPICIOUS | LIKELY_SYNTHETIC | INCONCLUSIVE│
│            + reasons[] + engine + model_version + calibration   │
└──────────────────────────────┬─────────────────────────────────┘
                               │ tokenized verdict only (no audio)
                               ▼
                  Citizen Risk Engine  ──▶  one-tap report
```

**Why a frontend + a model:** the frontend is cheap, explainable, and gives the
stage something to point at ("it flagged the flat spectrum"); the model does the
real work; the calibrator makes the number usable by the Risk Engine; the
decision layer keeps the four verdicts honest.

### Model choice (offline, open weights, CPU-viable)

| Option | Why | Why not | Verdict |
|---|---|---|---|
| **AASIST / AASIST-L** (graph-attention anti-spoof) | Best-documented open anti-spoof family; ASVspoof 2019/2021 baselines exist; INT8-distils acceptably | Trained on ASVspoof conditions, not Indian telephony; licence check needed | **Primary** |
| **RawNet2 / RawNet3** | End-to-end, no feature engineering | Heavier on CPU; weaker on codecs | Fallback / ensemble member |
| **LFCC + GMM / LCNN** | Very light, strong spectral baseline | Older; brittle to unseen codecs | Baseline to beat (§6) |
| **Whisper-derived embeddings + linear probe** | Cheap, robust features | Not an anti-spoof model; large embedder | Only if a probe measures well |
| Proprietary/cloud detector | — | Violates offline + no-egress | **Forbidden** |

Track the choice in `citizen/voiceguard/MODEL_CARD.md` (create it) with
licence, provenance hash, training conditions, and known failure modes. A model
without a card does not ship.

---

## 5. Build order and how to build each item

### M0 — Rename and register (30 min)

Add a `# MAYA` header comment to `voiceguard/voiceguard.py`, a line in
`raksha/ARCHITECTURE.md §3` and `CONTEXT.md §7` glossary, and a
`CHANGELOG.md` entry. Done when `grep -ri maya` finds the module, the glossary,
and the changelog — and nothing contradicts itself.

### M1 — Capture and the honest buffer (P0, ~1 day)

Mirror `CITIZEN_APP_BUILD.md` C-11, but with Maya's stricter contract:

```js
// maya-capture.worklet.js — 3 s ring, 16 kHz, zeroable
this.buf = new Float32Array(16000 * 3);
stop() { this.buf.fill(0); this.port.postMessage({zeroed: true}); }
```

Requirements: explicit user gesture to start · persistent visible indicator ·
buffer zeroed on stop **and** on tab blur · no `localStorage`/`indexedDB`/
`fetch` in the capture module (asserted by a grep test) · `MediaStreamTrack.stop()`
called on teardown.

**Done when:** a synthetic WAV round-trips through the worklet at 16 kHz ±2 %;
the zero-fill is observed by test; the indicator is asserted in the DOM; the
grep test fails the build if storage or network APIs appear.

### M2 — Feature parity in the browser (P0, ~1 day)

Port `_features()` to JS and add the anti-spoof frontend in Python first (it is
easier to test), then mirror it:

```python
def frontend(x16k: np.ndarray, sr=16000, n_mels=64, win=400, hop=160) -> np.ndarray:
    """log-mel (or LFCC) with first/second deltas, 1.5 s window."""
    # STFT → |X|² → mel filterbank → log → Δ, ΔΔ → (T, 3·n_mels)
```

**Done when:** Python and JS frontends agree within 1e-3 on the same WAV (golden
vector committed); feature extraction < 15 ms for 1.5 s on a mid-range phone.

### M3 — Train / distil / quantise the model (P0, the real work)

1. **Data.** You need three sets, kept strictly separate:
   - *train/val*: public anti-spoof corpora (ASVspoof 2019 LA + 2021 DF, plus
     any openly licensed Indian-language TTS/real pairs — check licences per
     corpus and record them in the model card).
   - *in-domain val*: **synthetic Indian telephony** — take a licensed real-speech
     set and a set of open TTS systems, then apply realistic narrowband +
     codec simulation (8 kHz resample, μ-law, packet loss, AGC, background
     noise) to both classes. This is the step almost everyone skips, and it is
     the whole ballgame for Indian scam calls.
   - *test (held out)*: never used for anything but the §6 table.
2. **Train** AASIST-L (small variant first — you need phone CPU, not SOTA on a
   server). Keep an LFCC-GMM baseline to prove the model is worth its bytes.
3. **Distil + quantise:** knowledge-distil the teacher into the small student,
   then ONNX **INT8 dynamic** quantisation. Target ≤ 8 MB.
4. **Calibrate:** fit temperature/isotonic on the *in-domain* val split; store
   the calibrator parameters alongside the model. A raw sigmoid is not a
   probability.
5. **Card it:** write `MODEL_CARD.md` — data provenance, licence, training
   conditions, known failure modes, intended use, **explicit non-use**
   ("advisory screen, not forensic proof").

**Done when:** the ONNX file + frontend + calibrator are committed *or* fetched
by a documented, pinned script; a golden-vector test proves the Python reference
and the ONNX model produce the same score within 1e-3; the model card exists and
lists every dataset licence.

**Safety:** do not add any real human voice recording to the repo without
consent. Ship fixtures as synthetic or openly licensed only.

### M4 — Decision layer with reasons (P0, ~half day)

Keep the four verdicts; add one:

| Verdict | When | Citizen-facing copy (en) |
|---|---|---|
| `SILENT` | `rms < 1e-4` | "We couldn't hear anything. Try again." |
| `SUSPICIOUS` | frontend-only anomaly, or `p > 0.5` uncalibrated | "This audio looks machine-generated. Ask a question only a person could answer." |
| `LIKELY_SYNTHETIC` | `p_clone ≥ 0.80` and calibrated | "This is probably an AI-generated voice. Hang up. Call the number on your card." |
| `INCONCLUSIVE` | everything else, all errors, `p` in the war zone | "We can't tell. Treat it as suspicious if they ask for money, OTP, or an 'arrest'." |

`reasons[]` must be plain-language and **derived from interpretable evidence** —
e.g. "unusually flat spectrum", "voice pauses are mechanically regular",
"no breath sounds between sentences". Never expose raw scores to a citizen
without a sentence explaining them. Thresholds live in one constants block.

**Done when:** every verdict path has a test, every string has hi/te variants,
and `INCONCLUSIVE` is proven to be the default for unmodelled audio.

### M5 — On-device integration (P0, ~1 day)

`citizen/app/infer/maya-web.js` loading `model.onnx` via
`onnxruntime-web` (WASM; WebGPU behind a capability probe). Serve from
`StaticFiles` under `/app/infer/`, cached by the existing service worker.

**Done when:** inference < 400 ms p95 on a mid-range Android, measured and
recorded; zero network requests during screening (asserted by a fetch spy);
works with the network fully disabled; model cached offline.

### M6 — Measurement (P1, gates every claim)

Publish **all** of these, per condition, with the test set named:

| Metric | Why | Target to beat |
|---|---|---|
| **EER** (equal error rate) | Standard anti-spoof number | must beat the LFCC-GMM baseline on the same test set; report absolute numbers |
| **min t-DCF** | The ASVspoof-recommended operational metric | report, do not optimise blindly |
| **Accuracy per condition** | narrowband 8 kHz, μ-law, packet loss 1–5 %, noise SNR 5/10/20 dB, re-encoded | show the degradation curve — this *is* the honesty |
| **Per-language breakdown** | en / hi / te speakers, Indian accents | no aggregate that hides a weak language |
| **Latency p50/p95** | on-device, per 1.5 s window | ≤ 400 ms p95 |
| **FPR on real human calls** | the number that decides whether anyone keeps the app | report it first, not last |

Write the table into `raksha/EVALS.md` under a new "Maya" section and link the
model card. **No adjective may appear where a number belongs**
(`BUILD_GUIDE.md §6`). If the model loses to the baseline on Indian telephony,
publish that — it is more credible than a silent omission.

**Done when:** `python -m evals.run_maya` reproduces every cell; the table is
frozen with a date and a model hash.

### M7 — Live-call screening (P2, needs the native wrapper)

PWA cannot tap call audio. Two honest paths:

- **Android `ConnectionService`/`AudioPlaybackCapture`** in the TWA wrapper
  (`CITIZEN_APP_BUILD.md` C-12) — capture the remote party's downlink only,
  with a persistent notification and one-tap stop. Requires `CAPTURE_AUDIO_OUTPUT`
  / assistant-role privileges and a clear legal review (recording consent law
  varies; store nothing).
- **"Put the call on speaker, tap Listen"** — no special permissions, works
  everywhere, worse UX. Ship this first; it is honest and demoable.

**Done when:** speaker-mode path runs end-to-end with the 2-second window and
emits a verdict while the call is live; the ledger/report path carries only the
tokenized verdict; the app never uploads audio.

### M8 — Consent, retention proof, and privacy tests (P1, parallel)

A `consent.json` schema (what is captured, why, for how long, how to stop),
rendered as a real screen, with a server-side record of the *decision* only
(no audio). Add a **privacy test suite**: microphone permission only on gesture;
buffer zeroed on stop/blur/teardown; no storage API in capture/infer modules; no
`fetch` with audio payloads anywhere; service worker never caches `/api/`.

---

## 6. Acceptance criteria for calling Maya "a voice-clone detector"

All six must be true, and the table must be published:

- [ ] A trained, open-weight model ships with a model card and licence record
- [ ] It beats the LFCC-GMM baseline on the **held-out Indian-telephony** set
- [ ] Calibrated probabilities (not raw logits) feed the Risk Engine
- [ ] EER **and** FPR-on-real-humans are published per condition and language
- [ ] Inference is fully on-device, offline, < 400 ms p95 on a mid-range Android
- [ ] Every verdict has a plain-language reason and a human next action

Until then the payload keeps the `NOT a trained anti-spoof model` label, and the
demo script says "heuristic screen — the trained model is the next milestone."
That sentence is a strength, not an embarrassment: it is the difference between
a team that reports its limits and a team that gets caught.

---

## 7. Demo script (what to actually show, honestly)

**Act 1 — the plumbing (30 s).** Tap Check Voice. Point at the visible indicator
and say: "three-second ring buffer, zeroed on stop, nothing leaves this phone."

**Act 2 — the fallback works (30 s).** Play the bundled synthetic tone → 
`SUSPICIOUS`, reason "pure-tone-like signal: trivially synthetic". Say plainly:
"this is the trivial case; it does not prove clone detection."

**Act 3 — the hard case (60 s).** Play a real human recording **and** a
clone of the same sentence. Show what the build actually returns. If both are
`INCONCLUSIVE`, say so — then show the *measured* table from M6 and the trained
model roadmap. Judges reward this; a fake green light gets destroyed in Q&A.

**Act 4 — the citizen path (30 s).** File the report; show the campaign id
fusing with the Sentinel leg on the SOC console; show 1930 as the next action.

**Never on stage:** "we detect deepfakes", "99 % accurate", or any number not
in `raksha/EVALS.md`.

---

## 8. Risks and their mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Model overfits ASVspoof conditions, fails on real Indian telephony | Silent false negatives in the field | In-domain val set (§M3.1) is the gate, not the ASVspoof number |
| Indian-language TTS data is scarce/licensed restrictively | Cannot generalise | Generate with open TTS + real licensed speech; record licences; test per language |
| INT8 quantisation collapses accuracy | Worse than baseline | Golden-vector + per-condition eval on the *quantised* model, not the float one |
| On-device latency on cheap phones | Unusable UX | AASIST-L + 1.5 s window; publish p95; degrade to frontend-only verdict and say so |
| Someone relabels `INCONCLUSIVE` as `SAFE` to make a demo look better | A fraud victim trusts a fake green light | A test greps for the labels; doctrine in `CITIZEN_APP_BUILD.md §6` rule 1 |
| Legal exposure from call audio capture | Pilot blocked | §M7: speaker-mode path first, capture-only with consent later, store nothing |
| **`features.md` never arrives and scope drifts** | Rebuilt against the wrong spec | Reconcile against §2 when supplied; log the delta in `CHANGELOG.md` |

---

## 9. Definition of done (Maya milestone)

- [ ] M0 rename registered in docs + changelog
- [ ] M1 capture with enforced 3 s ring buffer, indicator, zero-fill
- [ ] M2 browser/Python feature parity against a golden vector
- [ ] M3 trained + calibrated INT8 ONNX model with a model card
- [ ] M4 five verdicts with human-readable reasons and hi/te strings
- [ ] M5 fully offline on-device inference, measured latency
- [ ] M6 measured table in `raksha/EVALS.md` (EER, min t-DCF, per-condition,
      per-language, FPR on humans)
- [ ] M8 consent + privacy test suite green
- [ ] The `NOT a trained anti-spoof model` label is removed **only** when §6 is
      fully satisfied — and its removal is its own changelog entry
