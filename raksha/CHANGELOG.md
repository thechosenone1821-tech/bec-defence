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

## Unreleased / parked

- RAAVAN `playbook.yaml` (10 techniques, fixtures, expected defenses)
- Eval harness implementation (`evals/`)
- Citizen app repo creation decision
- Hackathon date + team rosters for the two parallel builds
- Verification of all [VERIFY] statistics (PIB, CERT-In, AIIMS)
