# RAKSHA — Phase 4: Consolidate the Citizen app, excluding VoiceGuard

> **Status:** Phase 4 implemented and deterministically validated · **Date:** 2026-11-26 · **Branch:** `arena/3b136fd9-bec-defence`
>
> **Maintainer instruction for this phase:** proceed to the next phase **without
> running any AI models**. No LLM/Commander, MAYA classifier, model endpoint or
> generative model inference was invoked. VoiceGuard / MAYA remain untouched.
>
> **Companions:** [`COMBINED_SYSTEM_ROADMAP.md`](COMBINED_SYSTEM_ROADMAP.md),
> [`PHASE3_CONTRACT_SPINE.md`](PHASE3_CONTRACT_SPINE.md),
> [`adr/ADR-011-unified-contracts.md`](adr/ADR-011-unified-contracts.md),
> [`adr/ADR-012-citizen-consolidation.md`](adr/ADR-012-citizen-consolidation.md).

---

## 1. Scope delivered

Phase 4 consolidates **one phone-first Citizen service and one PWA shell** for
all non-voice features. It does **not** merge the two app roots, start Phase 5,
or integrate VoiceGuard/MAYA.

| Deliverable | Location |
| --- | --- |
| One Citizen service | `apps/citizen/api.py`; legacy `citizen.api` resolves through the existing compatibility alias |
| One physical PWA shell | `raksha-code/citizen/app/index.html` + `manifest.json`, exposed through `apps/citizen/app` symlink |
| App-owned citizen sentences | `apps/citizen/copy.py` |
| Shared i18n/reason-rendering contract | `packages/contracts/i18n.py` |
| Hard-disabled feature flags | `apps/citizen/features.py` |
| Documented disabled VoiceGuard interface | `apps/citizen/voiceguard_interface.py` |
| Model-free consent/retention gate | `apps/citizen/retention.py` |
| Runtime-only honest shell overlay | `apps/citizen/phase4_shell.py` |
| Deterministic boundary checker | `tools/check_phase4_citizen.py` |
| No-AI test runners / plugin | `tools/run_phase4_pytest.py`, `tools/run_phase4_node_tests.py`, `tools/phase4_no_ai_plugin.py` |
| Acceptance tests | `tests/test_phase4_citizen.py`, `raksha-code/tests/test_phase4_citizen_compat.py` |

## 2. One service, one shell

The Citizen service is still the single `build_app()` in `apps/citizen/api.py`.
`raksha-code/citizen/api.py` and `raksha-code/apps/citizen/api.py` are
compatibility symlinks/aliases to that same physical file. The single PWA shell
is the frozen `raksha-code/citizen/app/` directory; `apps/citizen/app` is a
symlink, not a second shell.

`/api/citizen/capabilities` and `/api/citizen/features` now enumerate
`screen_message`, `assess`, `report`, offline queue, panic/1930, family mode and
retention under one service. Report events remain signed through the Phase 3
shared envelope and still carry no raw note, message text, audio or phone number.

## 3. Shared rendering, app-owned copy

`packages/contracts/i18n.py` owns language normalisation, bounded fallback
logging, reason-family lookup and the rendering algorithms. It imports no app
code, no VoiceGuard code and no AI model.

`apps/citizen/copy.py` owns every citizen-facing sentence: message verdicts,
families, `MSG-*` reason overrides, risk-band copy, advisory copy, band-reason
copy, source sentences, report copy, disclaimers and the new voice-tab notice.
It was populated by AST extraction of the frozen copy tables; the frozen
VoiceGuard package was not imported during generation and is not imported at
runtime.

`apps/citizen/risk/engine.py` and `fusion.py` now use the app copy module and
shared verdict constants. `apps/citizen/api.py` uses the same copy module for
message explanations, disclaimers, report explanations, language lists and
voice-tab status. Legacy `citizen.voiceguard.i18n` remains unchanged for
historical tests.

## 4. VoiceGuard / MAYA frozen behind a disabled flag

- `VOICEGUARD_ENABLED = False` and `NO_AI_MODELS = True` are hard-coded in
  `apps/citizen/features.py`; there is no environment override.
- `voiceguard_interface.py` documents the future `status()` / `screen()` seam
  and ships a `DisabledVoiceGuard` implementation. It has no import from
  `citizen.voiceguard`, no MAYA model, no capture worklet and no inference call.
- `/api/citizen/screen_voice` still enforces consent and the 3.5 s retention
  ceiling through the model-free `retention.py`, then returns an honest
  `NOT_INTEGRATED` / `INCONCLUSIVE` response. Samples are not processed, stored,
  echoed or scored.
- `/api/citizen/features`, `/api/citizen/health` and the capability card report
  `voiceguard.enabled=false`, `status="not integrated yet"` and
  `model_invoked=false`.
- The frozen VoiceGuard/MAYA tree, PWA capture assets, model artefacts, corpus,
  voice tests, `run_maya.py`, model card and historical specs were not edited.
  `tools/check_frozen_assets.py` still pins 28 assets.

## 5. Honest voice tab, no clone claim

The frozen `index.html` and `manifest.json` are **not edited**. The Citizen
service injects a page-relative `phase4.js` script into the single shell
response, serves it from `/app/phase4.js` (with the `/_citizen/phase4.js`
alias retained), and serves an honest manifest description at runtime. No
frozen file is written.

The injected script:

- changes the voice tab/button copy to **"Voice check — not integrated yet"**;
- replaces the voice hint and result with the same honest notice;
- clones and disables `btnScreenVoice` / `btnVoiceTone`, dropping their frozen
  event listeners without editing `app.js`;
- exposes `window.RakshaPhase4VoiceStatus` with `enabled:false`,
  `status:"not integrated yet"`, and `modelInvoked:false`;
- never calls `fetch`, `score_voice`, a model, or the microphone.

The runtime manifest says voice screening is not integrated yet and contains no
`voice-clone`, `clone detection`, or AI-model claim. The app-owned Phase 4 text
contains no `SAFE` verdict.

## 6. Preserved invariants

| Invariant | Enforcement |
| --- | --- |
| No raw score to a citizen | `explain_message()` excludes score/hits; UI renders the explanation |
| No SAFE verdict | risk bands and app copy contain no SAFE verdict; checker scans the copy catalogue and runtime shell |
| No PII leaves the phone | report endpoint signs category/severity/opaque token only; test asserts note absent |
| Fail-closed signature + Governor | Phase 3 envelope/action gate unchanged; report still signs through shared envelope |
| Offline queue / panic / family / retention / 1930 | one capability card; frozen PWA assets remain in the single shell |
| No AI model invocation | feature flags, interface, model-free retention, active-import checker and clean-process probe |

## 7. Verification

The maintainer's "don't run any AI models" instruction was enforced with an
explicit skip policy. `tools/run_phase4_pytest.py` ignores **23**
model-dependent Python test files (frozen VoiceGuard/MAYA, SLM/Commander,
spine-bus or old `/screen_voice` tests), and `tools/run_phase4_node_tests.py`
skips the one frozen MAYA capture Node test file. `tools/phase4_no_ai_plugin.py`
fails the pytest session if any VoiceGuard/MAYA/SLM/Commander module loads.
The exact list is auditable in those files.

Reproduce the validation:

```bash
python tools/run_phase4_pytest.py              # 186 passed, 0 failed, 4 warnings
(cd raksha-code && python ../tools/run_phase4_pytest.py)  # 171 passed
python tools/run_phase4_node_tests.py         # 60 passed
python tools/check_phase4_citizen.py
python tools/check_phase3_contracts.py
python -m packages.contracts
python tools/check_frozen_assets.py
(cd raksha-code && python evals/messageguard/run_evals.py --check)
python -m compileall -q apps packages tools tests
git diff --check
```

| Check | Result |
| --- | --- |
| Root no-AI pytest | **186 passed**, 0 failed, 4 warnings |
| Legacy-cwd no-AI pytest | **171 passed**, 0 failed, 4 warnings |
| Deterministic Node tests | **60 passed**, 0 failed |
| Total passing checks | **246** (186 Python root + 60 Node; legacy cwd is a subset) |
| Phase 4 / Phase 3 checkers | OK / OK |
| Config pins / frozen assets | 5 pins unchanged / 28 assets unchanged |
| MessageGuard eval `--check` | OK |
| `compileall` / `git diff --check` | clean / clean |
| Local links | **279/279** |
| Import smoke | no AI/VoiceGuard/MAYA/SLM modules loaded; VoiceGuard disabled |
| Model-free entrypoint helps | 5 OK |

No AI model-dependent test file, `run_maya.py` invocation, Commander endpoint,
Ollama call, generative model inference or model endpoint was run during Phase 4
or Phase 5 validation. The counts above are the Phase 5 no-AI revalidation of
this Phase 4 suite; see
[`PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md).
Older full-suite numbers remain historical snapshots; current
authority is [`../BUILD_STATE.md`](../docs/STATUS.md), [`EVALS.md`](../EVALS.md),
[`../specs/07_spine.md`](../specs/07_spine.md) and [`CHANGELOG.md`](CHANGELOG.md).

## 8. Scope honesty

This is a **Citizen contract-and-copy consolidation**, not a detector rewrite.
Phase 5 (MessageGuard single-source / alternative-tree port) is **not started**.
Earlier phase reports remain historical snapshots; the current authority is this
file plus `../BUILD_STATE.md`. No commit or push was requested.

> **Historical Phase 4/5 counts:** the numbers above are preserved as-of that
> phase. Current verified counts and the Phase 6–8 implementation are in
> [`PHASE678_UNIFIED_INTEGRATION.md`](PHASE678_UNIFIED_INTEGRATION.md) and [`../BUILD_STATE.md`](../docs/STATUS.md).
