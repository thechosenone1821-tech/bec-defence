# ADR-004 — One dry-run containment planner

> **Status:** Frozen for Phase 1 planning · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §5, [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 7

## Context

Containment planning exists in three forms:

- `../../raksha-code/spine/containment.py` — current exhaustive minimum-disruption cut over `company_topology.json`, objective `J = C + λD + μR + νA`.
- `../../archive/provenance/raksha-governance/raksha-governance/raksha/planner.py` — Part 5 exhaustive planner over a fixture topology with sign-off and crown-edge pricing.
- `../../archive/provenance/raksha-enterprise/raksha-enterprise/raksha/pipeline/planner.py` and `topology.py` — Part 6 BFS blast-radius proposals, ICU cut and egress-only fallback.

Two planners would mean two topology grammars, two cost functions, and two
different stories for why a cut was or was not refused.

## Decision

There is **one containment-planning capability**.

- **Canonical home (Phase 1):** `../../raksha-code/spine/containment.py` and its
  pinned topology/config files.
- **Port sources only:** governance and enterprise planner/topology modules are
  sources for exhaustive search, sign-off pricing, BFS blast-radius math,
  fallbacks and refusal tests. They are not independent planners.
- **Future target:** `packages/governance/planner.py` with one topology file and
  one objective function after Phase 7.
- **Execution rule:** the planner may only propose dry-run actions. It never
  severs a real edge, host, VLAN, session or service. Every proposal goes to
  ADR-003's Governor.

## Consequences

**Positive**

- One topology grammar and one pinned deployment config.
- One objective function, with hand-picked weights explicitly labelled as such.
- One blast-radius number per proposal.
- One place to enforce crown-jewel / Tier-0 impossibility.

**Costs / work deferred**

- Phase 7 must reconcile fixture topology JSON, enterprise packaged topology and
  the current `company_topology.json`.
- Phase 7 must reconcile exhaustive cut search with BFS fallback proposals.
- Phase 9 must label all planner numbers as fixture measurements.

## Safety and honesty gates

- No live containment action is enabled by this ADR.
- No hand-picked λ / μ / ν weight is presented as tuned from outcomes.
- No proposal can bypass the Governor or the ledger.
- Phase 1 adds no code; no safety rail is relaxed.

## Verification

- Source-of-truth matrix names one current canonical planner.
- ADR-003 holds final veto; ADR-002 seals the decision.
- Phase 1 exit gate: "no capability has two canonical homes" is satisfied for
  containment planning.
