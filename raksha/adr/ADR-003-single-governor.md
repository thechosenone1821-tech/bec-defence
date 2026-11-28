> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../../docs/STATUS.md); see the [retired code note](../../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# ADR-003 — One Governor and safety core

> **Status:** Frozen for Phase 1 planning · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §5, [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 7

## Context

The repo contains three Governor/safety-core lineages:

- `../../raksha-code/spine/governor.py` plus `tcb_core.py`, `tcb_mirror.py`,
  `watchdog.py`, `approval_token.py` and `tool_schemas.json` — current shipped deterministic Governor.
- `../../archive/provenance/raksha-governance/raksha-governance/raksha/governor.py` plus `tools.py`,
  `policy.py`, `budgets.py`, `fido2.py`, `tcb.py`, `watchdog.py` — Part 5 five-invariant implementation and TCB twins.
- `../../archive/provenance/raksha-enterprise/raksha-enterprise/raksha/pipeline/governor.py` — Part 6 G1–G4 rules with first-class refusals and fallbacks.

The doctrine is "AI proposes, the Governor disposes"; more than one final veto
would create a bypass by choosing the friendlier Governor.

## Decision

There is **one Governor capability**.

- **Canonical home (Phase 1):** `../../raksha-code/spine/governor.py` and its
  shipped safety-core modules.
- **Port sources only:** governance and enterprise Governor modules contribute
  invariants, schema locks, blast-radius budgets, FIDO2 step-up, TCB twins,
  watchdog behaviour, G1–G4 precedence, refusals and fallbacks. They are not
  second authorities.
- **Future target:** `packages/governance/` after Phase 7, with one 10-tool
  allowlist, one policy order, one TCB pair and one executor gate.
- **Binding rule:** every proposal from Commander, planner, console, Citizen
  report rail or RAAVAN replay passes through the one Governor before any
  dry-run executor is invoked.

## Consequences

**Positive**

- One final veto.
- One closed-world tool schema.
- One crown-jewel / Tier-0 lock.
- One blast-radius budget and FIDO2 step-up story.
- Refusals, escalations and internal guard failures all land in ADR-002's ledger.

**Costs / work deferred**

- Phase 7 must reconcile `G1–G4` with the five-invariant governance core.
- Phase 7 must decide one twin/TCB implementation while preserving fail-closed
  behaviour on disagreement.
- Phase 10 must retire duplicate Governors into provenance.

## Safety and honesty gates

- No "temporarily skip the Governor" path is allowed, even in demos.
- No admin override can buy a crown-jewel cut or an uptime-floor violation.
- No AI model output is treated as an approval.
- Phase 1 adds no code; no safety rail is relaxed.

## Verification

- Source-of-truth matrix names one current canonical safety-core package.
- ADR-002 supplies the single ledger write path for terminal outcomes.
- ADR-004 supplies proposals but never bypasses this Governor.
