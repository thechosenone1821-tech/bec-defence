# RAKSHA — Changelog

> Living log. **Protocol:** every substantive change appends an entry here —
> never rewrite history, append corrections. Format:
> `## [version] — date — author — summary` then bullets of substance.

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

## [0.8.0] — 2026-11-23 — VoiceGuard build session — Acoustic core, ONNX boundary, consent-gated API

- Replaced the tone-only VoiceGuard stub with bounded two-second, 16 kHz
  mono input validation and deterministic spectral/LFCC/LPCC descriptors.
- Preserved the conservative fallback: degenerate signal anomalies may be
  flagged, but ordinary speech remains INCONCLUSIVE without a supplied model.
- Added an optional ONNX Runtime adapter with a documented waveform/output
  contract. No trained weights or performance claims are bundled.
- Added explicit API consent gating, a strict 32,000-sample cap, sample-rate
  validation, model-readiness reporting, and request-memory-only audio handling.
- Focused local suite: 19 VoiceGuard/model/API tests passed. This is not a
  claim that the repository-wide suite has run in this environment.
- The browser UI and PWA microphone flow are still pending; browser capture
  is not an operating-system phone-call interception capability.
- Added `raksha/features.md` as a transparent source-backed inventory because
  no pre-existing `features.md` or Maya path was present in `main_final`.

## [0.9.0] — 2026-11-23 — VoiceGuard build session — Consent-first PWA microphone UX

- Replaced the bundled sample-tone demo with user-started two-second
  microphone capture, explicit consent, visible recording state, a cancel
  control, 16 kHz mono resampling, and track cleanup on completion/failure.
- Consent withdrawal cancels in-flight capture before submission; page exit
  stops active recording and microphone tracks. Temporary sample arrays are
  zeroed after screening.
- Updated offline-shell cache version; API paths remain excluded from caching.
- Added five PWA privacy/behavior regression checks. JavaScript syntax check
  passed; focused VoiceGuard/model/API/PWA suite: 24 passed locally.
- Browser capture screens a sample the user records. It does not access
  operating-system phone-call audio, and the configured service receives the
  explicitly consented sample for processing.

## [0.9.1] — 2026-11-23 — VoiceGuard build session — Phase 5 handoff audit

- Audited the final branch tree and restored the optional ONNX adapter and its
  mock-session tests after an intermediate stale-tree commit omitted them.
- Added a regression test ensuring screened audio and derived feature vectors
  are not attached to the Citizen incident-report event.
- Hardened page-exit cleanup: active capture is marked cancelled and consent
  cleared before recorder and microphone tracks are stopped.
- Focused isolated test workspace: 24/24 tests passed; JavaScript syntax check
  passed. These are focused checks, not the full repository suite.
- Full repository pytest/service smoke suite remains unverified because the
  sandbox could not clone the repository (network/DNS unavailable). A real
  browser microphone session also remains a manual release gate.

## Unreleased / parked

- RAAVAN `playbook.yaml` (10 techniques, fixtures, expected defenses)
- Eval harness implementation (`evals/`)
- Citizen app repo creation decision
- Hackathon date + team rosters for the two parallel builds
- Verification of all [VERIFY] statistics (PIB, CERT-In, AIIMS)
