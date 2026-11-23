# RAKSHA Citizen — what is built, what to build, how to build it

> **Last updated:** 2026-11-23 · **Owner of record:** repo maintainer (human)
> **Evidence base:** `raksha-code/citizen/`, `raksha-code/tests/`, `raksha/*.md`,
> and a full read-through + test run of the working tree on 2026-11-23
> (`pytest -q` → **67 passed**; `python evals/run_evals.py` → table reproduced).
> **Companion docs:** `MAYA_BUILD.md` (the VoiceGuard deep spec) ·
> `INFRA_BUILD.md` (Sentinel side) · `raksha/ARCHITECTURE.md §3` ·
> `raksha/BUILD_GUIDE.md` (M3).
> **Note:** `features.md` does not exist anywhere in this repository (checked
> working tree, every commit on every branch, git history, and the deleted
> `spectral-defence-poc (1).zip`). This file treats `raksha/ARCHITECTURE.md §3`,
> `raksha/BUILD_GUIDE.md §3 (M3)` and `raksha/ROADMAP.md` as the requirement
> source. When `features.md` is supplied, reconcile it against §3 of this file
> and log the delta in `raksha/CHANGELOG.md`.

**Status vocabulary used throughout:**
`BUILT` = runs and is covered by tests · `PARTIAL` = runs, contract incomplete ·
`STUB` = labelled placeholder, deliberately not the real thing ·
`ABSENT` = no code exists.

---

## 1. What the Citizen app is — and is not

**Is:** an offline-first, Android-first PWA plus a same-origin FastAPI service
(`python -m citizen.api --port 8095`) that screens scam messages, screens call
audio for synthetic-speech red flags (Maya/VoiceGuard — today a heuristic, see
`MAYA_BUILD.md`), and files a signed, tokenized incident report into the shared
spine so infra-layer evidence can fuse with it into one campaign.

**Is not:** the mass-market product. It is a **demo-grade reference build**
(`raksha/README.md` status line; `CHANGELOG.md` v0.4.0). There is no trained
voice model, no microphone capture, no risk fusion engine, no local report
queue, and no measured real-world accuracy anywhere. Every one of those is
listed below as work to build.

**Non-goals that never change** (`ARCHITECTURE.md §3`): no call-recording
retention · no IME/keystroke access · no mandatory account · no silent
exfiltration of any content to any server, including ours.

---

## 2. Verified built state

Run it before reading further:

```bash
cd raksha-code
pip install -r requirements.txt
pytest -q                              # 67 passed
python -m citizen.api --port 8095      # PWA + API on :8095
```

| # | Capability | Status | Evidence (path · test) | Honest limit |
|---|---|---|---|---|
| C-01 | PWA shell, 4 tabs (home / message / voice / report), installable manifest, offline service-worker shell | BUILT | `citizen/app/{index.html,app.js,styles.css,sw.js,manifest.json}`; `tests/test_citizen_api.py` | English UI only; no hi/te UI strings |
| C-02 | MessageGuard v0 — deterministic signal-family scorer, en/hi/te | BUILT | `citizen/messageguard/scorer.py` (144 LOC); `tests/test_messageguard.py` (5) | **20/20 = 1.00 on a synthetic hand-authored corpus only.** Rules, not a classifier. Will miss novel scripts; will false-positive on genuine urgent bank alerts |
| C-03 | VoiceGuard v0 — interface + spectral fallback (Maya) | STUB (labelled) | `citizen/voiceguard/voiceguard.py` (66 LOC); `tests/test_voiceguard.py` (6) | Flags only degenerate audio (pure tones, silence, white noise). Cannot detect a neural voice clone. Engine string literally embeds `NOT a trained anti-spoof model`. Full spec → `MAYA_BUILD.md` |
| C-04 | Screen endpoints | BUILT | `POST /api/citizen/screen_message`, `POST /api/citizen/screen_voice`; `citizen/api.py` | `screen_message` accepts `lang` but the scorer ignores it (cross-language token set is applied blind) |
| C-05 | One-tap report rail — HMAC-signed event, category + severity band + optional opaque `case_id`, no PII | BUILT | `citizen/api.py::report`, `spine/telemetry_mac.py::sign_event`; `tests/test_citizen_api.py`, `tests/test_m1_campaign_flow.py` | Forwarding only works when `RAKSHA_BUS_URL` is set. See **BUG-1** below — the offline message is currently false |
| C-06 | Citizen leg of the shared campaign graph | BUILT | `CHANGELOG.md` v0.5.0 — citizen `case_id` fuses with infra legs into one `cmp_*`; `tests/test_raavan_killchain.py` | Sandbox `case_id` tokens are low-entropy fixtures (dictionary-able). Production needs high-entropy randoms or a 1930/CERT-In-issued token |
| C-07 | 1930 helpline linkage | PARTIAL | `index.html` (`<a href="tel:1930">`), every verdict payload carries `"helpline": "1930"` | Not in the tab bar; buried inside the report panel. No IVR deep-link, no "call 1930 now" interstitial on a CRITICAL verdict |
| C-08 | Panic button (lock screen, kill known-scam sessions, call helpline) | ABSENT | `ARCHITECTURE.md §3` lists it; no code | Only a `tel:` link exists |
| C-09 | Citizen Risk Engine (fuse voice + message + SMS/UPI signals into one plain-language verdict) | ABSENT | `ARCHITECTURE.md §3`; no `citizen/risk/` module | Each screen scores in isolation; no combined verdict, no "why" narrative |
| C-10 | Family mode (stricter defaults for elders / first-time users) | ABSENT | `ARCHITECTURE.md §3`; `ROADMAP.md` Phase 2 | No profile, no local model, no louder warnings |
| C-11 | Microphone capture / real call audio path | ABSENT | `citizen/app/app.js` — the voice tab synthesises a 440 Hz tone in JS (`synthTone()`) and posts it | The app has never analysed a real recording. This is the single biggest demo gap |
| C-12 | SMS / UPI-notification ingestion (Android) | ABSENT | `ARCHITECTURE.md §3` ("optional SMS/UPI-notify signals") | Needs a native bridge; PWA cannot read SMS |
| C-13 | On-device inference | ABSENT | All scoring is Python on the server side of the same process | Audio crosses the network boundary as JSON floats — not acceptable for pilot privacy posture |
| C-14 | Local report queue + offline sync | ABSENT | `citizen/api.py` — no store exists | See **BUG-1** |
| C-15 | Real-world accuracy measurement | ABSENT | `CHANGELOG.md` v0.4.0, `raksha/EVALS.md` — explicitly "UNMEASURED" | No consented corpus, no precision/recall on real traffic |
| C-16 | Consent flow / zero-retention proof UI | ABSENT | No consent screen; retention is absent-by-construction only | Needs an explicit, auditable consent record before any voice work ships |

### Two honesty bugs to fix first (both are cheap, both matter)

**BUG-1 — the offline report path lies to a scam victim.** In
`citizen/api.py::_sign_and_forward`, when `RAKSHA_BUS_URL` is unset the
response says `"report stored locally (demo mode)"`, and `app.js` renders
`"✓ noted (offline mode — will sync)"`. **Nothing is stored and nothing syncs.**
A person who just lost money is told their report will be delivered. Fix:
either implement C-14 (persist to IndexedDB, honest "queued on this device,
will send when online" with a visible pending count) or change the copy to
"not sent — call 1930 now". Also change `"✓ reached Raksha response network"`
to "✓ received by the demo bus" — it reaches a sandbox, not a response network.

**BUG-2 — `lang` is accepted and ignored.** `screen_message` takes
`lang: en|hi|te|auto` and never passes it to `score_message` (whose signature is
`score_message(text)` only). Either thread it through (preferred: per-language
token weighting) or drop it from the contract. Leaving a parameter that silently
does nothing is doc drift.

**BUG-3 — `LOW` means both "clean" and "I have no idea", and nothing renders
differently anyway.** Verified 2026-11-23:

- `score_message("")` → `verdict: "LOW"`, reason `"empty input"`.
- `score_message("Hi mom, dinner at 8?")` → `verdict: "LOW"`, reason
  `"no known scam signals present"`.

An empty input and a benign message are indistinguishable to a caller. Combined
with the band table (`_BANDS`, no `UNKNOWN` member), the app has **no way to
express "I don't know"** on the message path — which is the single most
important sentence a citizen-facing detector must be able to say (see §6 rule 1).

**Correction (2026-11-23, same session):** an earlier draft of this file claimed
the UI "does not differentiate severity at all". **That was wrong** — I grepped
for `.verdict\.` and missed that `styles.css:36` styles the bare band classes:

```css
.LOW { color: var(--accent); } .MODERATE { color: #ffd166; }
.HIGH { color: #ff9f43; } .CRITICAL { color: var(--danger); }
```

So severity **is** colour-coded. Two real, smaller problems remain:

1. Colour is the **only** differentiator — no icon, no left border, no size
   change. `.CRITICAL` and `.LOW` differ only in hue, which fails for
   colour-blind users and on a sunny screen in a village. Pair colour with an
   icon and the word.
2. `app.js` hardcodes `class="verdict LOW"` on the report-success panel
   ("REPORTED"), so a successful report of a *critical* fraud renders green.
   The report panel should not reuse the message-severity scale at all.

Fix, in one small PR:

1. Add a fifth band `LOW_CONFIDENCE` for empty/short/no-signal input, ordered
   **below** `LOW` in `_ORDER` so `verdict_at_least` keeps working, and return
   it from the empty-input branch. Add its CSS class.
2. Pair every band with a glyph + left border, not just a colour:
   `.verdict.CRITICAL { color: var(--danger); border-left: 4px solid var(--danger); background:#2a1215; }`
   and render `data-icon` per band.
3. Stop reusing severity bands for the report acknowledgement — give it its own
   `.ack` class.
4. Update `test_messageguard.py` to assert the empty-input band explicitly, and
   add a test that every band in `_ORDER` has a `.verdict.<BAND>`-reachable
   style rule (parse the stylesheet).

---

## 3. Gap register (build order)

| Priority | ID | Work item | Why now | Source |
|---|---|---|---|---|
| **P0** | C-01b | Fix BUG-1 + BUG-2 + BUG-3 | A false "we got your report" is the worst possible message to a fraud victim; a green LOW that means "unknown" is the second worst | this audit |
| **P0** | C-11 | Real microphone capture (AudioWorklet, 16 kHz, ring buffer < 3 s, visible indicator) | Unlocks every voice feature on stage | `ARCHITECTURE.md §3`, `BUILD_GUIDE.md §5.5` |
| **P0** | C-03b | Maya v1: trained anti-spoof model behind the existing contract | The promise of the app; see `MAYA_BUILD.md` | `ARCHITECTURE.md §3` |
| **P0** | C-13 | On-device inference (onnxruntime-web) so audio never leaves the phone | Privacy doctrine; district-hospital/pilot requirement | `CONTEXT.md §6` |
| **P1** | C-09 | Citizen Risk Engine — one fused verdict + plain-language reasons | Turns three toys into one product | `ARCHITECTURE.md §3` |
| **P1** | C-14 | Local report queue + background sync + pending badge | Makes offline-first true | BUG-1 |
| **P1** | C-07b | 1930 as a first-class action: persistent button + CRITICAL interstitial | Safety-critical UI | `ARCHITECTURE.md §3` |
| **P1** | C-08 | Panic button (screen lock, kill scam sessions, dial 1930) | Advertised, absent | `ARCHITECTURE.md §3` |
| **P2** | C-10 | Family mode | Reach; elders are the primary target | `ARCHITECTURE.md §3`, `ROADMAP.md` Phase 2 |
| **P2** | C-17 | Multilingual UI (hi/te/en) + icon/voice-first layout | `CONTEXT.md §6` — low-literacy UX | `CONTEXT.md §6` |
| **P2** | C-12 | SMS/UPI notification ingestion via a thin Android wrapper | Highest-value passive signal | `ARCHITECTURE.md §3` |
| **P3** | C-15 | Consented corpus + measured precision/recall + multilingual parity | Gate before any pilot claim | `BUILD_GUIDE.md §6` |
| **P3** | C-18 | Signed OTA updates, DPDP alignment, consent records | Pilot prerequisite | `ROADMAP.md` Phase 2/3 |

---

## 4. How to build each item

### C-01b — Fix the three honesty bugs (half a day, do it first)

Files: `citizen/api.py`, `citizen/messageguard/scorer.py`,
`citizen/app/{app.js,styles.css}`, `tests/test_citizen_api.py`,
`tests/test_messageguard.py`.

```python
# citizen/api.py — no bus configured, nothing persisted:
return {"forwarded": False,
        "reason": "NOT_SENT_NO_BUS",           # machine-readable, not prose
        "event_id": signed.get("event_id"),
        "guidance": "Call 1930 now if money has moved."}

# citizen/app/app.js — render truth, not hope:
const sent = v.forwarded && v.forwarded.forwarded;
repOut.innerHTML = `<div class="verdict ${sent ? "LOW" : "MODERATE"}">${sent ? "REPORTED" : "NOT SENT"}</div>
  <div>${sent ? "Received by the demo bus." : "This device has no connection to Raksha. Nothing was stored. Call 1930 now — your data did not leave this phone."}</div>
  <div class="helpline">If you lost money, call 1930 and freeze the transaction.</div>`;
```

Then BUG-3, in the same PR:

```python
# citizen/messageguard/scorer.py
_BANDS = ((0.20, "LOW"), (0.45, "MODERATE"), (0.70, "HIGH"), (1.01, "CRITICAL"))
_ORDER = {"LOW_CONFIDENCE": -1, "LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}

def score_message(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if len(raw) < 12:                      # too short to judge — say so
        return {"verdict": "LOW_CONFIDENCE", "score": 0.0, "hits": {},
                "families_hit": [], "reasons": ["too little text to assess"],
                "engine": "messageguard-rules-v0 (synthetic-tuned)"}
```

```css
/* citizen/app/styles.css — severity must be visible, not implied */
.verdict.LOW_CONFIDENCE { color: #8a94a6; }
.verdict.LOW            { color: #5ad1a0; }
.verdict.MODERATE       { color: #f0b429; }
.verdict.HIGH           { color: #ff7a45; }
.verdict.CRITICAL       { color: #ff4d4f; background: #2a0d0f; padding: .5rem .75rem; border-radius: .5rem; }
.verdict::before        { content: attr(data-icon); margin-right: .4rem; }  /* icon + word, never colour alone */
```

Done when: a test asserts the offline response **never** contains the words
"stored" or "sync"; empty and short input return `LOW_CONFIDENCE`; every band
in `_ORDER` has a matching `.verdict.<BAND>` CSS rule (parse the stylesheet in
the test); `test_citizen_api.py` covers both branches; and `app.js` passes
`data-icon` per band so colour is never the only signal.

---

### C-11 — Real microphone capture (the unlock)

**Where:** `citizen/app/audio-capture.js` (new), wired into the voice tab of
`app.js`. No build step, no framework — matches the existing zero-dependency
rule in `BUILD_GUIDE.md §1`.

**How:**

1. Capture at 48 kHz in an `AudioWorkletProcessor`, decimate ×3 to 16 kHz in
   WASM-free JS (a simple 3-tap averaging decimator is honest and sufficient;
   document the anti-alias limit).
2. Keep a **rolling 3-second ring buffer only** (`Int16Array`), discard the
   tail continuously. Nothing is written to disk, IndexedDB, or `fetch` —
   enforced by review + a test that greps the module for storage APIs.
3. Show a **visible recording indicator** for the whole capture window
   (`BUILD_GUIDE.md §5.5`). On stop, the buffer is scored and then zeroed
   (`buffer.fill(0)`).
4. Emit 16 kHz `Float32Array` chunks; reuse the existing endpoint shape
   (`{samples: [...]}`) until C-13 lands, then switch to in-page WASM.

```js
// sketch — audio-capture.js
class Capture extends AudioWorkletProcessor {
  constructor() { super(); this.buf = new Int16Array(16000 * 3); this.i = 0; }
  process(inputs) {
    const ch = inputs[0]?.[0]; if (!ch) return true;
    for (let n = 0; n < ch.length; n += 3) {                 // naive 48k -> 16k
      const v = Math.max(-1, Math.min(1, (ch[n] + ch[n+1] + ch[n+2]) / 3));
      this.buf[this.i++ % this.buf.length] = v * 32767;      // ring; oldest overwritten
    }
    this.port.postMessage({filled: Math.min(this.i, this.buf.length)});
    return true;
  }
}
registerProcessor("raksha-capture", Capture);
```

**Done when:** a Playwright/pytest-js test drives a synthetic WAV through the
capture module and gets 16 kHz mono output within ±2 % of expected length; a
grep test proves no `localStorage|indexedDB|fetch` in the capture module; the
indicator renders in the DOM while capturing; buffer is zeroed on stop.

**Safety:** never auto-start capture. Microphone permission is requested only
from an explicit user gesture, and the UI states in plain language that audio
is discarded.

---

### C-13 — On-device inference

**Where:** `citizen/app/infer/` — `model.onnx` (INT8, produced by
`MAYA_BUILD.md` M3), `ort-config.js`, `maya-web.js`. Serve via
`StaticFiles` under `/app/infer/`.

**How:** `onnxruntime-web`, WASM backend first (broadest Android coverage),
WebGPU/WebNN behind a capability probe. Keep the Python path as the reference
implementation; a parity test must show the JS and Python front-ends produce
the same features within 1e-3 on the same WAV.

Contract stays: `score(audioFloat32) → {verdict, score, engine, reason, features}`.
Add `engine: "maya-onnx-int8-v1"` and keep the honesty string whenever the
model is not a trained detector.

**Done when:** first inference < 400 ms on a mid-range Android device (measured,
documented, not asserted); zero network calls during screening (asserted by a
service-worker/`fetch` spy test); model < 8 MB; parity test green.

---

### C-09 — Citizen Risk Engine (the missing product core)

**Where:** `citizen/risk/engine.py` + `POST /api/citizen/assess`.

**How:** fuse independent, differently-sourced signals with an explicit,
inspectable rule set — never a black box:

| Signal | Source | Weight w_i | Notes |
|---|---|---|---|
| Message verdict band | MessageGuard | 0.45 | HIGH/CRITICAL dominate |
| Voice verdict (`SUSPICIOUS`) | Maya | 0.40 | Only when a real model is behind it |
| Number/case linkage | report rail (`case_id` overlap with a live campaign) | 0.30 | Strongest single signal we have |
| Repeated contact attempt | local, on-device counter | 0.15 | Never leaves the phone |
| User-reported doubt | explicit tap | 0.10 | Respect the human |

Combine as a **bounded noisy-OR** (`1 − Π(1 − w_i)`), which cannot exceed 1.0
and is monotone — no calibration theatre. Emit **reasons as sentences**, built
from template strings per fired signal, in the user's language:

```json
{"risk": 0.87, "band": "CRITICAL",
 "reasons": ["This message demands your OTP — no bank ever does that.",
             "It claims an arrest is in progress. That is the 'digital arrest' script.",
             "The same sender pattern was reported by others in this campaign."],
 "advice": "Hang up. Do not pay. Call 1930.",
 "signals_used": ["message:credential", "message:authority", "campaign:cmp_612f..."]}
```

**Done when:** unit tests cover empty-input (must return `INCONCLUSIVE`, never
"safe"), single-signal, and all-signal cases; band thresholds are constants in
one place; every reason string has an en/hi/te variant; the response never
contains raw user text.

**Doctrine note:** the engine must be able to say **"I don't know."** A
no-signal result is `LOW_CONFIDENCE`, not `SAFE`. `cyberrakshak`-style projects
get this wrong and tell citizens a number is clean when it simply was not
reported yet — do not copy that failure mode.

---

### C-14 — Local report queue and honest sync

**Where:** `citizen/app/queue.js` (IndexedDB), `sw.js` background sync.

Store **only** the already-tokenized envelope (category, severity band, lang
digest, optional `case_id`, HMAC) plus a local `queued_at`. Never store the
message text or audio. Cap the queue (e.g. 200 entries) and show a pending
badge. On sync success, mark delivered; on 4xx, drop with a visible note; on
network error, retry with backoff.

**Done when:** airplane-mode test queues 3 reports, reconnect flushes them in
order, duplicates are suppressed by `event_id` (the bus already has a
`SeenEventCache`), and a storage-inspection test proves no raw content is in
IndexedDB.

---

### C-07b / C-08 — 1930 first-class + real panic behaviour

- Persistent, high-contrast **Call 1930** button in the header (not only inside
  the report panel).
- On a CRITICAL verdict, render a full-width interstitial: "This looks like the
  digital-arrest scam. Hang up now." with one tap to dial.
- Panic flow (PWA-safe subset): lock the view, clear sensitive inputs, revoke
  the page's own session token, open `tel:1930`. Anything beyond that —
  killing other apps' sessions — needs the native wrapper (C-12) and must say
  so instead of pretending.

**Done when:** the interstitial is keyboard/screen-reader accessible, the panic
flow is covered by a DOM test, and copy has hi/te variants.

---

### C-10 — Family mode

A local profile store (`citizen/app/profiles.js`): `guardian` (default for a
new user) and `standard`. Guardian raises every band one level, blocks dismissal
of a CRITICAL warning without an explicit "I understand" hold, and can pin a
trusted contact card. No server-side profile, ever.

**Done when:** band-shift logic is a pure function with table-driven tests, and
the stricter path is enforced server-side too when the request carries a
guardian flag (never trust the client).

---

### C-17 — Multilingual UX

Move all strings into `citizen/app/i18n/{en,hi,te}.json`; a `?lang=` +
`navigator.language` resolver; Devanagari and Telugu font stacks with correct
line-height (`styles.css` already sets a system stack). Keep every verdict
sentence short enough for a 360 px screen. Add a test that asserts key parity
across the three files (missing keys fail CI).

---

### C-12 — SMS / UPI ingestion (Android wrapper, P2)

PWA cannot read SMS. Ship a thin **Trusted Web Activity** wrapper with a
`NotificationListenerService` + SMS broadcast receiver that pipes *text* into
the same `screen_message` contract locally. Requirements: explicit per-source
consent, a visible list of what is monitored, offline-only by default, and a
one-tap kill switch. This is the highest-risk privacy surface in the whole
product — needs the maintainer's written sign-off before code lands
(`CONTEXT.md §8` open question 5).

---

### C-15 — Measurement before claims

| Metric | Corpus | Gate |
|---|---|---|
| MessageGuard precision / recall | consented + synthetic mix, en/hi/te | precision ≥ 0.90 on in-domain scripts; FPR published per language |
| Maya EER / min t-DCF | see `MAYA_BUILD.md` §6 | no claim until measured; report per codec condition |
| End-to-end false-positive rate | pilot traffic or offline replay | no "zero false positives" claims, ever |
| Time-to-verdict on device | mid-range Android | publish p50/p95, not a single hero number |

No adjective may replace a number (`BUILD_GUIDE.md §6`).

---

## 5. Test gates for every PR touching `citizen/`

```bash
cd raksha-code
pytest -q                                      # all suites, currently 67
pytest tests/test_citizen_api.py tests/test_messageguard.py tests/test_voiceguard.py -q
```

New behaviour needs, at minimum: one firing test, one silent/negative test, one
contract test (payload shape unchanged for the bus), and — for anything
touching audio — a **privacy test** asserting no raw audio or text is persisted
or transmitted. The report envelope must keep passing
`spine/telemetry_mac.verify_event` end-to-end (`test_m1_campaign_flow.py`).

---

## 6. Safety rules specific to the Citizen app (non-negotiable)

1. **Never say "safe."** Say "no known signal" or `LOW_CONFIDENCE`. Silence is
   not innocence. (Today the code returns `LOW` for both an empty string and a
   benign message — BUG-3. Fix it before writing any other UI copy.)
2. **Never store raw audio.** Ring buffer < 3 s, zeroed on stop, visible
   indicator (inherited from `BUILD_GUIDE.md §5.5`).
3. **Never upload content.** Only the tokenized envelope leaves the device;
   `entities` is `{}` unless the user supplies an opaque `case_id`.
4. **Every verdict ends with a human action** (call 1930 / don't pay / hang up).
   A verdict with no next step is a bug.
5. **Offline truthfulness.** If it was not sent, say it was not sent.
6. **No dark patterns.** No streaks, no fear-urgency, no upsell, no mandatory
   account.

---

## 7. Definition of done (Citizen milestone)

- [ ] BUG-1, BUG-2 and BUG-3 fixed, with tests
- [ ] Real mic capture + on-device Maya inference, zero network in the path
- [ ] Risk Engine with en/hi/te reasons and an explicit "I don't know" band
- [ ] Local queue with honest sync states
- [ ] 1930 first-class + panic flow
- [ ] Family mode and i18n
- [ ] Measured accuracy table in `raksha/EVALS.md` (no adjectives)
- [ ] `raksha/CHANGELOG.md` entry + `Last updated` bumped in every touched doc
- [ ] No safety rail relaxed; no new unverified number in any doc
