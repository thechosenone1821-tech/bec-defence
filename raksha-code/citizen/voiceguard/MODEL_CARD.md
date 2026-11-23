# MODEL CARD — `maya-lr-v1`

> **Created:** 2026-11-23 · **Status:** trained, unvalidated · **Artefact:**
> `maya_lr_v1.json` (734 bytes) · **SHA-256[0:16]:** `8b140095e5f8599e`
> This card travels with the model. If the artefact changes, this card is
> stale and must be regenerated (`python -m citizen.voiceguard.train`).

---

## 1. The one-line honesty statement

**This model has never heard a human being or a real voice clone.** It is
trained on a procedural synthetic corpus of my own construction, and every
number below describes that corpus — not the world. It is **not** a validated
anti-spoof model, and `contract.may_claim_clone_detection()` correctly returns
`False`.

---

## 2. Intended use

| | |
|---|---|
| **Intended** | A citizen-facing *screen*: "this call has machine-like production characteristics, be careful". One input to a risk score, never a verdict on its own |
| **Not intended** | Forensic evidence · accusation of a real person · law-enforcement use · any automated decision without a human in the loop |
| **Deployment** | On-device, offline, as part of RAKSHA Citizen. Never a server round-trip of audio |
| **Failure mode it prefers** | Saying "I don't know" (`INCONCLUSIVE`) over accusing a real person |

---

## 3. Model

| Property | Value |
|---|---|
| Family | L2-regularised logistic regression (numpy, no framework) |
| Parameters | 2 weights + 1 bias + 2 standardisation vectors + calibration |
| Size on disk | 734 bytes |
| Input | 2 scalar features per clip: `pause_cv`, `f0_cv` |
| Output | Calibrated P(spoof) ∈ [0,1]; threshold `0.9412` |
| Training time | ~10 s on one core |
| Inference time | ~15 ms per 2 s clip (dominated by the frontend, not the model) |
| Determinism | Seed `20260101` ⇒ byte-identical artefact |

**Equation (readable, complete):**

```text
z = -0.115  +  (-0.963)·((pause_cv - 0.1961) / 0.2741)
            +  (-0.873)·((f0_cv    - 0.0724) / 0.0475)
P(spoof) = sigmoid(z / 0.25)
warn when P(spoof) >= 0.9412
```

Both coefficients are **negative**: more pause irregularity and more pitch
variation both push the score toward *not synthetic*. That direction is the
one a human would draw, which is the only reassuring thing about this model.

### Why only two features

Feature selection was measured, not guessed. On the held-out split, with and
without 0.02 of added noise:

| Feature set | Clean EER | Noisy EER |
|---|---|---|
| 162 cepstral dims (LFCC+MFCC+deltas, mean/std pooled) | 0.000 | 0.667 |
| 9 hand-picked scalars incl. `spec_flatness`, `spec_flux` | 0.000 | 0.500 |
| 4 production cues | 0.167 | 0.278 |
| **2 production cues (shipped)** | **0.167** | **0.222** |

The cepstral model's perfect score was real for the corpus and worthless for
the world: `spec_flatness` moves 0.0056 → 0.1137 under added noise (noise
genuinely flattens a spectrum), so the model had learned "hissy line =
synthetic". Dropping the spectral cues and keeping the *production* cues costs
0.17 EER on clean synthetic data and buys a model that survives re-coding.

---

## 4. Training data — read every word of this

| | |
|---|---|
| Source | `citizen/voiceguard/corpus.py`, procedural generation |
| Real recordings | **NONE** |
| Real voice clones | **NONE** |
| Real TTS systems | **NONE** |
| Indian languages | **NONE** (no language at all — the generator produces vowels) |
| Clips | 60 per class × 3 splits = 360 total, 2 s each, 16 kHz mono |
| Split | 60 % train / 20 % val / 40→20 % test, disjoint seeds, no clip reused |

**Bona-fide-ish class:** additive formant synthesis with cycle-to-cycle jitter,
amplitude shimmer, an F0 random walk, breath noise on the voicing envelope,
gliding formants, and irregular pauses varying in both position and length.

**Spoof-ish class:** the same additive synthesis with *no* jitter, *no*
shimmer, *no* breath, a smooth macro-prosodic F0 drift, and pauses of identical
length at jittered positions.

**Known corpus artefacts** (each found the hard way during Phase 3):

1. Pause **depth** initially differed between classes (near-zero vs −30 dB).
   The classifier learned the generator's amplitude choice. Fixed by matching
   attenuation at 0.03 in both classes.
2. Pause **duty cycle** initially differed (~0 % vs ~20 % silence). Fixed by
   normalising both to ~20 %.
3. Cepstral **c0** (log-energy) flipped sign on the same clip under noise.
   Excluded from the model vector.
4. Spectral **flatness/flux** are channel properties, not speaker properties.
   Excluded after the noise sweep above.

Any one of these undetected would have produced a headline number that meant
nothing. They are listed so the next person does not re-learn them.

---

## 5. Measured results — SYNTHETIC CORPUS ONLY

Reproduce: `cd raksha-code && python -m citizen.voiceguard.train --dry-run`

| Split | n | EER | Accuracy | Precision | Recall | FPR |
|---|---|---|---|---|---|---|
| train | 108 | 0.287 | 0.7315 | 0.750 | 0.679 | 0.218 |
| val (used for calibration) | 36 | 0.167 | 0.806 | 0.800 | 0.842 | 0.235 |
| **test (held out)** | 36 | **0.167** | **0.861** | **0.933** | **0.778** | **0.056** |
| test + 0.02 broadband noise | 36 | 0.167 | 0.833 | 0.875 | 0.778 | 0.111 |

**Test accuracy 86.1 % on 36 synthetic clips.** The 95 % confidence interval on
36 samples is roughly ±11 points, so the true value on this corpus is somewhere
between 75 % and 97 %. Reporting it to four decimal places would be theatre.

**What these numbers do NOT mean:** anything about real speech, real TTS, real
codecs, real languages, or real scammers. They are a regression baseline.

---

## 6. Limitations — exhaustive, because this is where trust is earned

1. **No real data.** The single largest limitation. Everything above is a
   statement about `corpus.py`.
2. **No neural clones tested.** The corpus does not contain a single modern
   TTS output. A good neural clone is expected to pass this model as
   `INCONCLUSIVE`.
3. **Telephony is simulated crudely.** Phase 5 measured four degradations
   (`evals/run_maya.py`): an FFT brick-wall band-limit to 300–3400 Hz, an
   8-bit μ-law compander, 2 % packet loss at 20 ms, and additive Gaussian
   noise. These are *approximations*, not real codecs: no true 8 kHz
   resample, no G.729/AMR, no jitter, no echo, no AGC. Under band-limiting
   recall drops from 72.2 % to **38.9 %** (EER 0.167 → 0.278). Treat that as
   the best available indication that narrowband calls are substantially
   harder, not as a measurement of real call performance.
4. **No Indian languages or accents.** The generator has no phonetics.
5. **Two features.** It cannot distinguish "synthetic" from "unusual speaker",
   "reading aloud", "speech-to-text playback", or "someone speaking slowly".
6. **Calibration is fitted on 36 clips.** The temperature (0.25) and the
   threshold (0.9412) are far less reliable than their precision suggests.
7. **Silence and short clips are out of domain** — handled upstream as
   `SILENT` / `INCONCLUSIVE`, never scored.
8. **No adversarial testing.** Nobody has tried to evade it, and evasion is
   trivial: add natural pause variation and pitch wobble to your TTS.

---

## 7. Ethical and safety notes

- **Never accuse.** A positive verdict says "machine-like characteristics", not
  "this is a criminal".
- **False positives cost more than false negatives here.** A wrong "fake"
  verdict on a family member's voice destroys trust in the app permanently.
  This is why the threshold is chosen under a 5 % FPR ceiling rather than
  maximising accuracy.
- **The label stays until measured.** `contract.TRAINED_MODEL_PRESENT` is only
  set True when this artefact loads; `MEASURED_ON_REAL_SPEECH` stays False.
  Removing the honesty clause in `engine_label()` requires satisfying
  `MAYA_BUILD.md §6` in full — a real corpus, per-condition and per-language
  results, and a published FPR on real human calls.
- **No audio leaves the device.** The model is 734 bytes and runs locally;
  there is no reason for raw audio to travel, and no code path that does it.

---

## 8. Reproduction and provenance

```bash
cd raksha-code
python -m citizen.voiceguard.train --dry-run    # table only, writes nothing
python -m citizen.voiceguard.train              # regenerates the artefact
pytest tests/test_maya_phase3.py -q             # pins behaviour + determinism
```

The test suite asserts the artefact's SHA-256 prefix, so an accidental
retrain that changes the weights fails CI rather than silently shipping.

---

## 9. What the next person must do (Phase 5+)

1. Replace `corpus.py` with a **real** corpus (licensed real speech + open TTS
   output, with a licence record for each source).
2. Replace the simulated degradations with real codec round-trips (G.711 is
   approximated; G.729/AMR/Opus are absent) and re-run §5
   per condition.
3. Add at least hi/te/en speaker diversity and report per language.
4. Attempt evasion — build an adversarial test set before publishing anything.
5. Only then may `engine_label()` stop saying "NOT a validated anti-spoof
   model", and only with its own `CHANGELOG.md` entry.
