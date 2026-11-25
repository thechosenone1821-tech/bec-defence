# PART 2 — CITIZEN FEATURE: VOICEGUARD
## (Maya — synthetic-speech screening)

> **What this is.** The detector that listens to a short window of call audio and
> decides whether the voice on the other end is plausibly machine-generated.
>
> **Team size.** 2 people. **Depends on:** Part 1 (capture, reasons, i18n).
> **Can be built against stubs?** Yes for the app; no for the model.
>
> **Status: the pipeline is finished and honest. The model is not yet credible.**

---

## 1. What exists, precisely

| Piece | State |
|---|---|
| Frontend (LFCC/MFCC, 16 kHz, silence masking) | ✅ built and tested |
| Trained model | ⚠️ trained on a **synthetic corpus** — real-world accuracy unmeasured |
| Calibration | ✅ temperature-scaled, threshold chosen for a 5% FPR ceiling |
| Reason codes + plain-language output | ✅ built |
| Model card | ✅ written, including 8 stated limitations |
| Measurement harness | ✅ six degradation conditions |
| Real-speech evaluation | ❌ **never done** |
| Neural clone evaluation | ❌ **never done** |

### 1.1 Measured results — synthetic corpus only

| | EER | accuracy | recall | FPR |
|---|---|---|---|---|
| held-out test (n=36) | 0.167 | 86.1% | 72.2% | 0.0% |
| **narrowband telephony** | **0.278** | **69.4%** | **38.9%** | 0.0% |

**Read the second row, not the first.** On telephone-bandwidth audio — which is
what a real call *is* — recall falls to 39%. The cue the model relies on lives
partly in the high band, and a phone call removes it. This is the single most
important number in this document, and it is the reason the model is not
described as an anti-spoof product.

---

## 2. Why the model looks the way it does

The shipped classifier uses **two features**: `pause_cv` (variation in pause
lengths) and `f0_cv` (variation in pitch). Not 162 cepstral dimensions, which is
what a textbook would suggest. The reason is measured, not aesthetic:

| feature set | EER clean | EER + noise |
|---|---|---|
| 162 cepstral dims | 0.000 | **0.667** |
| 9 spectral scalars | 0.000 | 0.500 |
| 4 production cues | 0.167 | 0.278 |
| **2 production cues (shipped)** | **0.167** | **0.222** |

The 162-dimension model scored a **perfect** clean EER. That was the warning, not
the win: it had learned "hissy line = synthetic", because the noise genuinely
flattens spectra. Spectral cues describe the **channel**, not the speaker.

**Rule for anyone continuing this work:** an EER of 0.000 is a bug report.

---

## 3. The honesty gate

Three flags govern what may be claimed, and a test enforces them:

| Flag | Value | Meaning |
|---|---|---|
| `TRAINED_MODEL_PRESENT` | `True` | an artefact exists |
| `MEASURED_ON_REAL_SPEECH` | `False` | it has never seen a real recording |
| `may_claim_clone_detection()` | **`False`** | therefore nothing may be claimed |

Every API response carries:

> *"maya maya-lr-v1 (trained on SYNTHETIC corpus — real-world accuracy
> UNMEASURED; NOT a validated anti-spoof model)"*

Do not remove this string to make a slide look better. It is the product's only
defence against being believed too much.

---

## 4. What requires model training

This is the part of RAKSHA that genuinely needs ML, and only this part.

| Task | Data needed | Effort |
|---|---|---|
| **Real speech corpus** | 8–10k clips, Indian-accented, both classes | 3–4 weeks incl. collection and consent |
| **Modern neural clones** | 2–3 TTS/clone systems, licence permitting | 1–2 weeks |
| **Retrain + recalibrate** | — | 2–3 days |
| **Telephony robustness** | real codec round-trips (G.729/AMR/Opus) | 1 week |
| **On-device quantisation** | ONNX INT8 export + phone benchmark | 1 week |

Until the first two rows exist, **do not raise the accuracy claim.** The pipeline
is ready to receive a real model; that is the honest status.

---

## 5. Build order

1. Frontend + feature contract (done)
2. Corpus builder with class parity on confounders (done)
3. Model + temperature calibration + FPR-constrained threshold (done)
4. Measurement harness with degradation conditions (done)
5. **Real corpus** ← the actual blocker
6. Quantised on-device model

---

## 6. Definition of done

- [x] Deterministic: same input ⇒ same verdict
- [x] Never raises; degrades to `INCONCLUSIVE` with a reason
- [x] Silence and unjudgeable input **never** reach the model
- [x] Threshold chosen against an FPR ceiling, not for accuracy
- [x] One public calibrated probability path
- [x] Measured on synthetic corpus and labelled as such
- [ ] Measured on real speech *(blocks any accuracy claim)*
- [ ] Measured against a neural clone *(blocks the word "clone")*

---

## 7. Known failure modes

1. **Telephony.** 39% recall on narrowband. Will miss real calls.
2. **Good clones.** A modern neural clone is expected to pass as `INCONCLUSIVE`.
3. **Unusual speakers.** Cannot distinguish synthetic from reading aloud,
   playback, or an atypical speaker.
4. **Trivial evasion.** Add natural pause variation and pitch wobble to any TTS.
5. **No phonetics.** Nothing to say about Indian languages or accents.
