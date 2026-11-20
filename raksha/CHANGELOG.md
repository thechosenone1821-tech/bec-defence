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

## Unreleased / parked

- RAAVAN `playbook.yaml` (10 techniques, fixtures, expected defenses)
- Eval harness implementation (`evals/`)
- Citizen app repo creation decision
- Hackathon date + team rosters for the two parallel builds
- Verification of all [VERIFY] statistics (PIB, CERT-In, AIIMS)
