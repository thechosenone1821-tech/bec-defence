> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../docs/STATUS.md); see the [retired code note](../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# RAKSHA — Changelog

> Living log. **Protocol:** every substantive change appends an entry here —
> never rewrite history, append corrections. Format:
> `## [version] — date — author — summary` then bullets of substance.
> Test counts and engine strings inside older version entries are historical
> as-of that release; current verified state is the newest entry, the root
> `../CHANGELOG.md`, the single `../docs/STATUS.md`, generated `../EVALS.md`
> and `../evals/claims_ledger.json`.

## [1.0.0] — 2026-11-26 — deterministic Phase Nine and Ten closeout

- Replaced the evaluation sprawl with one deterministic corpus generator, one
  replay player, one eval runner, one generated `../EVALS.md`, one claims ledger
  and one drift check (`make eval` / `run_evals --check`).
- Added one install command, one test command, one eval command and one process
  launcher; added CI gates for Python suites, browser suites, eval drift, ledger
  verify, boot manifests, no secrets and no live-executor imports.
- Rewrote the root `README.md`, added `docs/STATUS.md`, `docs/README.md` and the
  root `CHANGELOG.md`; froze the ten-phase board and wrote the VoiceGuard
  re-entry gate for a separate future Phase Eleven.
- Moved retired standalone projects, historical root documents and legacy
  standalone eval/corpus/replay sources under `archive/provenance/` with
  `INTEGRATED.md` notes. Frozen VoiceGuard/MAYA assets remain unchanged.
- Every measured number now carries fixture / synthetic / sandbox /
  hand-authored / real-world UNMEASURED conditions and a claims-ledger source
  row. No real-world accuracy, latency, uptime, recall or false-positive claim
  is made from sandbox fixtures. Test counts below are historical; current gates
  are `make test`, `make eval` and CI.
- No AI model, Commander/SLM/Ollama endpoint, live executor, real containment,
  session revocation, host action, clone detection claim or field FPR claim was
  introduced. Dry-run remains the only executor mode.
- Added the root `../summary.md` AI handoff and future-integration playbook;
  it is covered by the claims ledger and the unified integration checker.

## [0.1.0] — 2026-11-20 — AI-assisted maintainer session — Initial documentation set

- Created `raksha/` as the single source of truth for the RAKSHA program
  (Citizen app + Sentinel app, one doctrine).
- Problem statement elevated to critical-infrastructure seriousness:
  formal advisory register (Part I) + 90-second spoken version (Part II);
  AIIMS/PIB/CERT-In figures preserved **unverified** with [VERIFY] tags —
  stage use blocked until resolved.
- Full project context written for AI collaborators: heritage map from
  eigenshield-v2 (Governor, TCB twins, ledger, sanitizer, Ring organs →
  Sentinel shields; Bragg lineage → Citizen MessageGuard).
- Architecture: two apps + shared spine; counterfactual containment
  formulated as constrained minimum-disruption cut (Reach = ∅ s.t.
  argmin C + λD + μR); RAAVAN red team scoped sandbox-only.
- Roadmap: Phase 0 docs → Phase 1 hackathon MVP (citizen + sentinel live
  demo, judges' turn) → Phase 2 hardening → Phase 3 pilots (one district
  hospital + one campus) → Phase 4 open-source release.
- Build guide: stack decisions, monorepo layout, M1 spine-first sequence,
  safety rules (dry-run default, Tier-0 human gate), testing/measurement
  gates, definition of done.
- `AI_HANDOFF.md` — operating rules, current-status table, doc-update
  protocol, escalation triggers.
- Third-party numbers remain UNVERIFIED; see `CONTEXT.md §5` and
  `PROBLEM_STATEMENT.md` checklist. Nothing merged to `main`; PR #1 open.

## [0.2.0] — 2026-11-20 — AI-assisted maintainer session — M1 spine shipped

- `raksha-code/` monorepo created; spine ported from eigenshield-v2
  (sanitizer, entity graph, ledger + anchor, Governor + TCB twins, tripwire,
  canary, boot manifest, telemetry MAC, bus, orchestrator, watchdog, slip
  client) and hardened: RAKSHA branding, package-relative boot manifest
  (portable), layout-aware manifest lookup in Governor.status().
- New in spine (not a straight port): attack-graph **campaign correlator v0**
  (deterministic union-find over shared entity tokens in the sliding window;
  stable `cmp_*` ids; exposed at `/api/state.campaigns`).
- Executor is a **labeled DRY_RUN stub** — no host is ever touched until the
  M2 Sentinel shields port the organs. Nothing executes for real.
- Porting is copy-with-adaptation, NOT runtime dependency on eigenshield-v2;
  that tree stays frozen as the reference build.
- Tests: 27/27 green incl. new `test_m1_campaign_flow.py` — the BUILD_GUIDE
  §M1 exit criterion: synthetic 3-event campaign flows bus → graph →
  Governor → ledger → `/api/state`; unsigned batch is held closed
  (`HELD_UNVERIFIED_EVIDENCE`); campaign fused as `cmp_*`.
- Live boot smoke (port 8090) verified the same flow with a real uvicorn
  process, `config_integrity: ok`, signed vs unsigned batch behavior.
- Known deltas: env vars still `EIGENSHIELD_*` (RAKSHA_* rename scheduled
  for v0.2 branding sweep); campaign correlator has no temporal kernel or
  weighted fingerprint yet; citizen app untouched.

## [0.3.0] — 2026-11-20 — AI-assisted maintainer session — M2 Sentinel shields shipped

- `raksha-code/sentinel/shields/` — all 8 organs ported from eigenshield-v2
  reflexes (ring1 identity, ring2 AI defense, ring3 endpoint, ring4 network
  healing) plus base_organ; tests carried over (test_organs, test_hashimoto,
  test_page_curve). 37/37 pytest green.
- Bus executor is now **organ-backed** (`executor_mode: "organ"` at
  /api/state + /api/health): tools route to the real shield RPCs, which are
  dry-run-safe by construction. Fallback to labeled `DRY_RUN_*` stubs is
  loud and automatic (unimportable shields), or forced via
  `RAKSHA_EXECUTOR=dry-run`. Nothing on any host is ever modified.
- Live smoke (port 8091): signed campaign => actions executed by organs
  (TRAP_DENSITY_BOOSTED, HOST_ISOLATED, SESSION_REVOKED), campaign fused
  (`cmp_612f5cec46`, size 3), config_integrity ok.
- Scope note: organs run through their designed safety surfaces (PageCurve
  never os.kill; percolation cuts virtual; MUTs is a control-surface
  simulation). Real CAP_BPF/eBPF paths remain out of scope and are labeled.
- Citizen app NOT started — next session per maintainer's sequencing
  (Sentinel first, then Citizen).

## [0.4.0] — 2026-11-20 — AI-assisted maintainer session — M3 Citizen app (demo-grade, honest) shipped

- `raksha-code/citizen/` — offline-first **PWA** + same-origin FastAPI
  service (`python -m citizen.api --port 8095`, live preview open):
  home / Check Message / Check Voice / Report screens, 1930 helpline
  panic button, service-worker offline shell, zero-PII reporting by
  construction (entities {} — category + severity band only, HMAC-signed).
- **MessageGuard v0** (`citizen/messageguard/scorer.py`): deterministic
  signal-family scorer for en/hi/te scam scripts (authority impersonation,
  credential grabs, money-action, prize, urgency, link-grab), tuned on a
  synthetic hand-authored corpus (12 scam + 8 clean, en/hi/te) — 20/20 =
  1.00 ON THE SYNTHETIC CORPUS. Real-world accuracy is UNMEASURED and
  presented nowhere as such.
- **VoiceGuard v0**: interface + spectral fallback only; verdicts
  SILENT/SUSPICIOUS/INCONCLUSIVE; INCONCLUSIVE is the default for real
  speech. NOT a trained anti-spoof model; UI labels itself accordingly.
- **Report rail** forwards a signed citizen event (`CITIZEN_REPORT_*`)
  to the spine bus; verified end-to-end in tests (verify_event passes,
  no raw content/PII in payload). Without RAKSHA_BUS_URL it honestly
  reports "stored locally (demo mode)".
- 54/54 pytest green across spine + shields + citizen.
- 2026-11-20 also: `/api/ingest` field `verified` documented; citizen
  event ring maps to RING_UNKNOWN at the sanitizer boundary (contract
  untouched — additive enum extension deferred to contract v2.2).
- Not done: on-device model for voice (trained AASIST/RawNet unknown),
  mic integration, fuse report signals into campaign correlator with
  infra-layer events (M4 glue).

## [0.5.0] — 2026-11-20 — AI-assisted maintainer session — M4 RAAVAN + cross-layer campaign fusion shipped

- `raksha-code/raavan/` — playbook.yaml (10 techniques, 6-stage canonical
  sequence, each mapped to fixture + expected defense) and killchain.py —
  an honest replay player that feeds SIGNED organ telemetry through the
  same pipeline real organs use (never a bypass; never a simulated
  orchestrator). CLI: `python -m raavan.killchain --bus-url http://127.0.0.1:8090`.
- **Citizen ↔ Sentinel fusion without contract changes**: optional
  `case_id` on citizen reports (validated, opaque; sanitizer digests it
  into a stable sha256 token). Citizen leg and all infrastructure legs
  land on ONE campaign. Caveat: sandbox case tokens are low-entropy
  fixtures (dictionary-able); production must mint high-entropy randoms
  or a CERT-In/1930-issued case token — parked for contract v2.2.
- Live run (fresh bus :8090): forged probe => HELD_UNVERIFIED_EVIDENCE;
  organ-signed campaign => full dry-run-safe execution (document
  quarantine, session revocation, trap boost, thermal-host isolation,
  human step-up at 0.96 severity); fused campaign cmp_d151562f8f,
  size 5, severity_max 0.96, organs touched CITIZEN_APP + 4 infra organs.
- Governor counter-attack gate test: RAAVAN's attempt to cut the ICU
  VLAN (preserve_tier0_vlans=false or Tier-0 in args) is hard-BLOCKED.
- 60/60 pytest green. Preview servers live on :8090 (Sentinel demo) and
  :8095 (Citizen demo) — ephemeral, sandbox-scoped.
- Parked: CASE_ entity prefix as additive contract v2.2 token; temporal-
  kernel campaign correlator; T06 lab cloud-audit fixture (M6).

## [0.6.0] — 2026-11-20 — AI-assisted maintainer session — M5 containment planner + Governor integration

- `spine/containment.py` — exhaustive minimum-disruption cut over the access
  layer of `company_topology.json` (10 non-crown edges — the whole space is
  enumerated, no heuristics, deterministic). Objective
  `J = C + λD + μR + νA` (cut size; fixture-flow fraction severed; residual
  mission-critical weight reachable by the attacker; count of
  clinical-adjacent severed roads) s.t. reachability seeds → Tier-0 == ∅.
  Crown-jewel edges never candidates; ICU/cold-chain/core-auth roads carry
  the ν penalty so they are cut only when unavoidable. Every number labeled
  FIXTURE-MEASURED.
- `POST /api/containment` on the bus (additive): seeds caller-supplied or
  derived live from the event buffer; builds a dry-run
  `execute_percolation_cut` action (measured rho_after clamped into the
  tool schema band) and submits it to the Governor — never executes itself.
- **Deep-implant finding (honest, doctrine-true):** once the attacker is in
  VLAN_CORP_IT, the cheapest isolating cut severs 44% of mission-critical
  fixture weight → Governor BLOCKS (below the 90% preserved-uptime floor) →
  human step-up. The system refuses autonomous core surgery by design.
- Ingress case (guest/maint/lab): 3 low/standard edges cut, 100% critical
  weight preserved, Governor APPROVED, dry-run PERCOLATION_CUT_APPROVED,
  ICU INTACT. `/api/state.last_containment` + `action_plan` WS frame +
  ledger `containment_plan` entry.
- Tests 60 → 67/67. Docs v0.6.0. Live previews on :8090 (Sentinel) and
  :8095 (Citizen).
- Parked: production NetFlow fixture; spectral-radius target as Governor
  context instead of tool-schema clamp; plan-cache per campaign.

## [0.7.0] — 2026-11-20 — AI-assisted maintainer session — M6 measured evals + docs freeze

- `raksha-code/evals/run_evals.py` — runs the fixtures end-to-end and prints
  the baseline×metric table (B1 threshold-alert, B2 signature list, B3 full
  isolation vs RAKSHA). Every cell measured this run: 1 fused campaign from
  the 5-step replay; 5/5 forged probes rejected (AI path held closed);
  containment severs 14.71% fixture flow with 100% mission-critical weight
  preserved (ICU INTACT, 0 tier-0 edges); deep-implant cut BLOCKED by the
  Governor 90% floor; MessageGuard 20/20 synthetic; sandbox wall-clock
  ingest→decision ~208 ms (not an SLA).
- `raksha/EVALS.md` — the frozen table, reproduction steps, illustrative
  ₹-saved arithmetic with every external input marked [VERIFY], and the
  explicit non-claims. Stage rehearsal / backup video / judges' script are
  human tasks — NOT done, not claimable from this sandbox.
- Docs frozen for rehearsal at v0.7.0. Tests 67/67.

## [0.8.0] — 2026-11-26 — AI-assisted maintainer session — MessageGuard v1 integrated

- Folded the standalone Part 3 tree at
  `../random project that ew need to integrate/raksha/` into the main
  application: `raksha-code/citizen/messageguard/` now carries the v1
  scorer, normalizer, band map, `MSG-*` reason catalogue, and en/hi/te regex
  token sets. `score_message()` remains the stable Citizen API contract;
  `analyze()` is the measured engine. The original staging tree is retained
  for provenance, not as a runtime source of truth.
- Added 492 hand-authored labelled JSONL fixtures (372 scam + 120 genuine)
  under `raksha-code/citizen/fixtures/messageguard/`. The 20-item M3 corpus
  remains a smoke test only and is explicitly not a measurement corpus.
- Added a reproducible harness at `raksha-code/evals/messageguard/` with
  `--check` drift detection and a generator for
  `raksha/MESSAGEGUARD_EVALS.md`. Measured on the shipped scorer:
  **99.2%** scam detection (369/372), **11.7%** false-positive rate (14/120),
  **96.5%** overall accuracy (475/492) at the >=MODERATE operating point —
  **hand-authored, in-distribution fixtures only; real-world UNMEASURED**.
- Wired the stable reason codes into `citizen/voiceguard/i18n.py` with
  en/hi/te sentences; `MSG-*` codes now reach the Citizen explanation layer
  without exposing raw scores, matched scam phrases, or internal family keys.
  Added 34 Python tests (23 ported scorer tests + 11 integration tests).
- Fixed two integration regressions: a Hindi negation cue matched the tail of
  `सत्यापन करें` and suppressed a real credential request; ASCII word
  boundaries failed after Indic combining marks in Telugu compatibility rows.
  Both have regression tests and neither changed the published eval numbers.
- Verified: **1252 pytest passed**, 1 skipped, 1 documented xfail; **90 Node
  browser tests passed**; `evals/messageguard/run_evals.py --check` green;
  M6 eval table reproduces with the new MessageGuard rows.
- Docs synced: `README.md`, `AI_HANDOFF.md`, `ARCHITECTURE.md`,
  `ROADMAP.md`, `BUILD_GUIDE.md`, `EVALS.md`, `MESSAGEGUARD_EVALS.md`,
  `../specs/00_INDEX.md`, `../specs/03_citizen_messageguard.md`,
  `../raksha-code/README.md`, `../BUILD_STATE.md`, and
  `../CITIZEN_APP_BUILD.md`. No safety rail was relaxed; the executor stays
  dry-run and VoiceGuard still does not claim clone detection.

## [0.8.1] — 2026-11-26 — AI-assisted maintainer session — Phase 1 combined-system architecture freeze (docs only)

- Completed **Phase 1 documentation** of the 10-phase combined-system roadmap.
  Added `raksha/PHASE1_ARCHITECTURE_FREEZE.md` (one system diagram, frozen
  two-app decisions, phase boundary and exit gate),
  `raksha/PHASE1_SOURCE_OF_TRUTH_MATRIX.md` (single-owner directory inventory
  and one canonical home per duplicated capability), and `raksha/adr/` with
  nine ADRs: ADR-001 bus, ADR-002 ledger, ADR-003 Governor, ADR-004 planner,
  ADR-005 organs, ADR-006 MessageGuard, ADR-007 eval runner, ADR-008 status
  document, ADR-009 VoiceGuard frozen seam.
- Added `raksha-code/citizen/voiceguard/FROZEN.md` to mark VoiceGuard / MAYA as
  parked by explicit maintainer request. VoiceGuard is not a Phase 1–10
  deliverable, is not an exit criterion, and receives no new accuracy,
  real-speech, or clone-detection claim.
- Synced stale planning headers in `README.md` (repo root), `raksha/README.md`,
  `raksha/ROADMAP.md`, `raksha/ARCHITECTURE.md`, `raksha/CONTEXT.md`,
  `raksha/AI_HANDOFF.md`, `raksha/COMBINED_SYSTEM_ROADMAP.md`,
  `raksha-code/README.md`, `specs/00_INDEX.md`, `VOICEGUARD_ROADMAP.md`, and
  `MAYA_BUILD.md` so historical docs point to the new Phase 1 authorities.
  Corrected the stale Maya name-status wording in `MAYA_BUILD.md`.
- **Docs-only change clearly marked.** No `.py`, `.js`, `.json`, `.yaml`, test,
  fixture, config, CI file, generated artifact, or safety rail was changed. No
  directory was moved or created at the target layout; no feature flag was added
  or toggled. Current verified runtime state remains the newest code-level
  entry above and `../BUILD_STATE.md`.
- **Judgment call notified:** "continue with phase 1" was treated as
  authorization for Phase 1 documentation, not for Phase 2 implementation. The
  five maintainer decisions in `COMBINED_SYSTEM_ROADMAP.md` §9 remain gated
  before any code moves.

## [0.8.2] — 2026-11-26 — AI-assisted maintainer session — Phase 2 separate-but-integrated code layout

- Implemented **Phase 2 code scaffold** with visible separation: new
  `apps/citizen/` and `apps/infra/` roots plus shared `packages/contracts`,
  `packages/spine`, `packages/governance`, and `packages/ledger` facades.
  Added [`PHASE2_CODE_LAYOUT.md`](PHASE2_CODE_LAYOUT.md) and
  [`adr/ADR-010-separation-boundaries.md`](adr/ADR-010-separation-boundaries.md).
- Moved editable Citizen Python modules into `apps/citizen/`; added
  `legacy_voiceguard.py` as the single adapter to the frozen seam. Added
  compatibility symlinks and a `citizen.* -> apps.citizen.*` package alias so
  legacy commands/tests keep working. Added Infra backend, detector and console
  boundary packages.
- Left **VoiceGuard / MAYA untouched**: no voice Python, model, capture, i18n,
  reason, PWA/Maya JS, `run_maya.py`, model card, or historical VoiceGuard spec
  content was edited. Added `tools/frozen_assets.sha256` and
  `tools/check_frozen_assets.py` to pin 28 frozen assets by SHA-256.
- Added `packages/contracts/separation.py`, root `pytest.ini`, root layout
  tests, and `raksha-code/tests/test_phase2_separation.py`. The boundary suite
  scans imports with `ast`, rejects direct app-to-app imports, checks independent
  app importability in subprocesses, and verifies frozen-asset hashes.
- Updated `corpora/real_documents.py` to count canonical non-symlink markdown
  paths only; Phase 2 compatibility symlinks otherwise duplicated docs. Synced
  `specs/04_infra_detection_rings.md` §5.4 and the calibration tests with the
  new canonical corpus. No detector threshold or safety rail was changed.
- Synced `README.md` (root), `raksha/README.md`, `raksha/AI_HANDOFF.md`,
  `raksha/COMBINED_SYSTEM_ROADMAP.md`, `raksha/PHASE1_ARCHITECTURE_FREEZE.md`,
  `raksha/PHASE1_SOURCE_OF_TRUTH_MATRIX.md`, `raksha/adr/README.md`, and
  `raksha-code/README.md` to the Phase 2 layout.
- Verified: **1259 pytest passed** from repo root (1 skipped, 1 xfailed),
  **1257 pytest passed** from `raksha-code/`, **90 Node tests passed**,
  MessageGuard `--check` green, frozen-asset checker green, `compileall` and
  `git diff --check` clean.
- **Scope honesty:** this is a separation-preserving scaffold, not a big-bang
  merge. `raksha-code/` remains a compatibility/provenance layer; Phase 3–10
  will move shared implementations, detectors, governance, evals, docs and root
  README into their final homes. No commit or push was requested.

## [0.8.3] — 2026-11-26 — AI-assisted maintainer session — Phase 3 unified shared contracts and spine

- Implemented **Phase 3 — Unify shared contracts and the spine** as code while
  preserving exactly two separate app roots. Added
  [`PHASE3_CONTRACT_SPINE.md`](PHASE3_CONTRACT_SPINE.md) and
  [`adr/ADR-011-unified-contracts.md`](adr/ADR-011-unified-contracts.md).
  At the time of this Phase 3 entry, Phase 4+ remained unauthorized; a later
  maintainer request authorized Phase 4 with no AI models run.
- Added one shared contract layer in `packages/contracts/`: canonical JSON,
  signed-envelope validation for `mac` / `signature` / `sig` profiles,
  `MSG-*` reason catalogue, verdict/legacy bands, config pins and auth scopes,
  sanitizer/entity rules, backend-route contract, reserved VoiceGuard slot,
  and a signature + Governor action gate. No VoiceGuard/MAYA implementation
  is imported.
- Added one `append / verify` ledger interface and one shared CLI in
  `packages/ledger/`; legacy `spine.ledger_cli` now delegates to it. Shipped
  spine telemetry MAC, BaseOrgan sealing, spine ledger hashing, enterprise I1
  canonical JSON, enterprise auth scopes, governance canonical serialisation,
  sanitizer, entity graph and boot manifest now delegate to `packages/`
  contracts. Their wire formats and legacy imports remain compatible.
- Made `apps/citizen/messageguard/{reasons,bandmap,scorer}.py` re-export or use
  the shared `MSG-*`, band and legacy-organ tables. Citizen health and Infra
  `/app/contract` expose the same event/backend contract. `SharedActionGate`
  requires a valid signature and Governor approval before any dry-run executor.
  `tools/check_phase3_contracts.py` AST-checks app imports against the
  no-bypass list.
- Added `tools/check_phase3_contracts.py`,
  `tests/test_phase3_root_contracts.py`,
  `raksha-code/tests/test_phase3_shared_contracts.py`, and
  `packages/contracts/config_pins.json`. Added 12 Phase 3 tests: one envelope
  validates identically across Citizen, RAAVAN, eval, enterprise I1 and sealed
  organ profiles; both ledger CLI entrypoints verify one populated chain; and
  unsigned/tampered/Governor-refused actions never reach the executor.
- Synced root `README.md`, `BUILD_STATE.md`, `CITIZEN_APP_BUILD.md`,
  `raksha/README.md`, `raksha/AI_HANDOFF.md`, `raksha/EVALS.md`,
  `raksha/ROADMAP.md`, `raksha/BUILD_GUIDE.md`, `raksha/ARCHITECTURE.md`,
  `raksha/CONTEXT.md`, `raksha/COMBINED_SYSTEM_ROADMAP.md`, Phase 1/2 report
  headers, ADR-010, the ADR register, `specs/00_INDEX.md`, `specs/07_spine.md`,
  `raksha-code/README.md`, `apps/`, `packages/` and `tools/` READMEs.
  Older release entries remain historical snapshots.
- **VoiceGuard/MAYA untouched:** no frozen source, PWA/Maya JS, model, capture,
  corpus, i18n, eval, model card, or historical VoiceGuard spec content was
  edited. `tools/check_frozen_assets.py` still pins 28 assets.
- Verified: **1271 pytest passed** from repo root (1 skipped, 1 xfailed),
  **1263 pytest passed** from `raksha-code/`, **90 Node tests passed**,
  Phase 3 contract checker green, 5 config pins unchanged, MessageGuard
  `--check` green, frozen-asset checker green, `compileall`, `git diff --check`,
  local-link check, import smoke and entrypoint help clean. Total documented
  passing checks: **1361** (1271 Python root + 90 Node).
- **Scope honesty:** this is a contract-and-compatibility unification, not a
  full runtime merge. `raksha-code/` remains the compatibility/provenance
  layer; full Governor, organ, RAAVAN/corpora/evals, docs/archive and packaging
  moves remain Phases 6–10. No commit or push was requested.

## [0.8.4] — 2026-11-26 — AI-assisted maintainer session — Phase 4 Citizen consolidation, no AI models run

- Implemented **Phase 4 — Consolidate the Citizen app, excluding
  VoiceGuard** as code. Added
  [`PHASE4_CITIZEN_CONSOLIDATION.md`](PHASE4_CITIZEN_CONSOLIDATION.md) and
  [`adr/ADR-012-citizen-consolidation.md`](adr/ADR-012-citizen-consolidation.md).
  Phase 5+ remains unauthorized. The maintainer explicitly required **no AI
  models**; no LLM/Commander, MAYA classifier, model endpoint, generative
  model inference, or model-dependent test file was run.
- Kept exactly one Citizen service and one physical PWA shell. Added
  `/api/citizen/features` and `/api/citizen/capabilities`; `screen_message`,
  `assess`, `report`, offline queue, panic/1930, family mode and retention
  remain under the same `apps/citizen/api.py` service.
- Moved i18n/reason-rendering logic into
  `packages/contracts/i18n.py` and citizen-facing en/hi/te sentences into
  `apps/citizen/copy.py`. `risk/engine.py`, `risk/fusion.py`, message
  explanations, disclaimers, report explanations, language lists and the
  voice-tab notice now use that split. The frozen VoiceGuard package was
  **not imported** during copy generation; tables were extracted with `ast`.
- Added `apps/citizen/features.py` with hard-disabled
  `VOICEGUARD_ENABLED=False`, `NO_AI_MODELS=True` and
  `commander_model=False`; added `apps/citizen/voiceguard_interface.py` with
  a documented `DisabledVoiceGuard`; added `apps/citizen/retention.py` as a
  model-free consent/retention gate. Active Citizen imports now load no
  frozen VoiceGuard or SLM module.
- `/api/citizen/screen_voice` returns an honest `NOT_INTEGRATED` /
  `INCONCLUSIVE` response after consent/size checks. Samples are never
  processed, stored, echoed or scored. `apps/citizen/phase4_shell.py`
  injects a runtime-only script into the single frozen shell and serves an
  honest manifest; the voice tab says **"not integrated yet"** and no
  clone-detection claim is added. Frozen PWA/VoiceGuard/MAYA files were not
  edited.
- Added `tools/check_phase4_citizen.py`,
  `tests/test_phase4_citizen.py`, and
  `raksha-code/tests/test_phase4_citizen_compat.py`. Added
  `tools/run_phase4_pytest.py`, `tools/phase4_no_ai_plugin.py` and
  `tools/run_phase4_node_tests.py`: 23 model-dependent Python test files and
  one frozen MAYA capture Node test file are skipped, and pytest fails if any
  forbidden model module loads. The checker proves one service/shell, disabled
  flags, app-owned copy, shared rendering, no model/frozen imports on the active
  path, honest runtime shell, preserved invariants, and frozen-asset hashes.
  Phase 3 checker/test comparisons with frozen i18n were changed to AST
  extraction so those deterministic checks do not import the frozen package.
- Synced the roadmap, ADR register, `BUILD_STATE.md`, `EVALS.md`,
  `specs/07_spine.md`, root/Raksha/raksha-code READMEs, `AI_HANDOFF.md`,
  Phase 1/2/3 report headers, ADR-010/011, `apps/`, `packages/` and
  `tools/` READMEs. Older release entries remain historical snapshots.
- **VoiceGuard/MAYA untouched:** no frozen source, PWA/Maya JS, model,
  capture, corpus, i18n, eval, model card, or historical VoiceGuard spec
  content was edited. `tools/check_frozen_assets.py` still pins 28 assets.
- Verification: root no-AI pytest **174 passed / 0 failed / 4 warnings**;
  legacy-cwd no-AI pytest **165 passed / 0 failed / 4 warnings**; deterministic
  Node tests **60 passed**; total **234 passing checks**. Phase 4 checker,
  Phase 3 checker, 5 config pins, 28 frozen assets, MessageGuard eval
  `--check`, `compileall`, `git diff --check`, **253/253** local links, no-model
  import smoke and 5 model-free entrypoint helps are green. No AI model module
  loaded in the pytest process. Full details are in `../BUILD_STATE.md` and
  `EVALS.md`.
- **Scope honesty:** this is a Citizen contract-and-copy consolidation, not
  a detector rewrite or full runtime merge. Alternative MessageGuard tree
  porting remains Phase 5; full Governor, organ, RAAVAN/corpora/evals,
  docs/archive and packaging moves remain Phases 6–10. No commit or push was
  requested.

## [0.8.5] — 2026-11-26 — AI-assisted maintainer session — Phase 5 MessageGuard single-source, no AI models run

- Made `apps/citizen/messageguard/` the one detector interface. Added
  `detect.py`, `tokens_hinglish.py`, `legacy_organ.py` and a sanitized
  `__main__.py`; rewrote the package exports and extended `scorer.py` with
  `auto/en/hi/te/hinglish` routing, deterministic language detection, 538
  fixtures and Hinglish negation guards. No independent `assess()` /
  `SignalFamilyScorer` or `msg.*` catalogue was ported.
- Ported 46 unique hand-authored Hinglish rows (30 scam, 16 benign) from the
  alternative Part 3 corpus into the one canonical 538-row corpus (402 scam,
  136 benign). Every ported row has `source` provenance and a unique normalized
  text; the other 385 alternative en/hi/te rows were deliberately not ported.
- Rewrote `raksha-code/evals/messageguard/run_evals.py` and
  `gen_evals_md.py`, regenerated `results.json` and
  `raksha/MESSAGEGUARD_EVALS.md`, and cleaned the generator's string literals
  so plain `lang="auto"` / `lang="hinglish"` quotes are byte-identical in the
  generated report. en/hi/te per-language aggregates are unchanged; current
  overall numbers are **99.2%** detection (399/402), **10.3%** FPR (14/136),
  **96.8%** accuracy (521/538), 96.6% precision and **UNMEASURED** real-world
  recall/FPR.
- Archived `raksha-messageguard/raksha/` and the standalone Part 3 snapshot
  under `archive/provenance/`, renamed their package directories to
  `messageguard_legacy`, added provenance notes and a collection-ignore
  conftest, and extended `tools/run_phase4_pytest.py` to ignore both archived
  test trees. `raksha.messageguard` is no longer importable from any repository
  root.
- Added `tools/check_phase5_messageguard.py`, `tools/check_local_links.py`,
  root/legacy Phase 5 tests,
  [`PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md)
  and [ADR-013](adr/ADR-013-messageguard-single-source.md). Synced current
  numbers, paths, phase status and verification commands across
  `BUILD_STATE.md`, `EVALS.md`, READMEs, specs, ADRs, roadmap and handoff.
- Verification: root no-AI pytest **186 passed / 0 failed / 4 warnings**;
  legacy-cwd no-AI pytest **171 passed / 0 failed / 4 warnings**; deterministic
  Node tests **60 passed**; total **246 passing checks**;
  **279/279** local Markdown links; MessageGuard eval `--check`, Phase 5
  single-source checker, Phase 4/3 checkers, 5 config pins, 28 frozen assets,
  `compileall` and `git diff --check` green. Source under test is **25,628**
  Python lines. No AI model module loaded in the pytest process; no
  LLM/Commander/SLM/Ollama/MAYA/VoiceGuard endpoint or inference was invoked.
- **Scope honesty:** this is a code/docs/corpus consolidation, not a field
  measurement, app-root merge or VoiceGuard/MAYA integration. Older release
  entries remain historical snapshots. Phase 6+ work remains pending. No
  commit or push was performed.

## [0.9.0] — 2026-11-26 — AI-assisted maintainer session — Phases 6–8 unified Infra integration

- Replaced the legacy `spine.bus` Infra facade with one deterministic runtime in
  [`../packages/spine/runtime.py`](../packages/spine/runtime.py); the app facade
  now injects the one detector contract and serves `/app/health`,
  `/app/contract`, `/app/console` and the canonical `/v1` API/WS surface.
- Added one 8-organ detection registry and `detect(event) -> DetectionResult`
  contract in [`../apps/infra/detectors/registry.py`](../apps/infra/detectors/registry.py),
  with firing, silent and missing-feature fixtures per organ. Unsigned, tampered,
  forged, malformed and unknown-organ events are quarantined before detection.
- Added one exhaustive/blast-radius planner, Governor and dry-run executor in
  [`../packages/governance/safety.py`](../packages/governance/safety.py), and one
  append-only runtime ledger in
  [`../packages/ledger/runtime_ledger.py`](../packages/ledger/runtime_ledger.py).
  Crown/Tier-0 cuts raise `UnsafeProposal`; admin override remains impossible;
  refusals are first-class ledger records sealed before API/WS broadcast.
- Added one read-only SOC console in
  [`../apps/infra/console/README.md`](../apps/infra/console/README.md) showing
  detection → proposal → decision → ledger sequence, refusals, quarantine,
  ledger verification, metrics and a read-scoped WS stream. It cannot mutate
  safety state. A deterministic synthetic fixture campaign is seeded so a judge
  can watch the sequence without `curl`.
- Added [`../tools/check_phase678_integration.py`](../tools/check_phase678_integration.py),
  [`../tests/test_phase678_integration.py`](../tests/test_phase678_integration.py),
  [`PHASE678_UNIFIED_INTEGRATION.md`](PHASE678_UNIFIED_INTEGRATION.md) and
  [ADR-014](adr/ADR-014-phase6-8-unified-integration.md). Synced roadmap,
  specs, READMEs, handoff, status and tools docs. VoiceGuard/MAYA remain frozen.
- Verification: root no-AI pytest **196 passed / 0 failed / 4 warnings**;
  legacy-cwd no-AI pytest **171 passed / 0 failed / 4 warnings**; deterministic
  Node tests **60 passed**; total **256 passing checks**; **336/336** local
  Markdown links; Phase 6–8/5/4/3 checkers, MessageGuard eval `--check`, 5
  config pins, 28 frozen assets, `compileall`, `git diff --check` and
  `git diff --cached --check` green. Source under test is **28,005** Python
  lines. No AI model module loaded in pytest; no LLM/Commander/SLM/Ollama/MAYA/
  VoiceGuard endpoint or inference was invoked.
- **Scope honesty:** Phases 6–8 only. No Phase 9/10 work, no app-root merge, no
  VoiceGuard/MAYA integration, no real containment and no real-world claim.
  Older entries remain historical snapshots. No commit or push was performed.

## Unreleased / parked

- RAAVAN `playbook.yaml` (10 techniques, fixtures, expected defenses)
- Citizen app repo creation decision
- Hackathon date + team rosters for the two parallel builds
- Verification of all [VERIFY] statistics (PIB, CERT-In, AIIMS)
- Consent-cleared, real-device message corpus and sender-ID allowlist
  (needed before any real-world MessageGuard accuracy claim)
