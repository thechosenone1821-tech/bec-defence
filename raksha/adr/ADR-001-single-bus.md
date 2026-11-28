> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../../docs/STATUS.md); see the [retired code note](../../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# ADR-001 — One telemetry bus and API/WS boundary

> **Status:** Frozen for Phase 1 planning · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §5, [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phases 3 and 8

## Context

The repo contains bus-like surfaces in three places:

- `../../raksha-code/spine/bus.py` — current shared FastAPI + WebSocket broker for verified-only ingest.
- `../../raksha-code/citizen/api.py` — current Citizen HTTP surface (`screen_message`, `screen_voice`, `report`, health).
- `../../archive/provenance/raksha-enterprise/raksha-enterprise/raksha/bus/` — Part 6 FastAPI app factory, scoped-token auth, WS hub and metrics-oriented backend.

Leaving all three as independent authorities would create three event envelopes,
three auth stories, and three broadcast paths. That would violate "one shared
spine" and could allow an app surface to bypass verification.

## Decision

There is **one logical bus capability**.

- **Canonical bus core (Phase 1):** `../../raksha-code/spine/bus.py`.
- **Allowed thin adapter:** `../../raksha-code/citizen/api.py` and future
  `apps/*/api.py` surfaces may translate app-specific HTTP into spine calls, but
  may not define a second envelope, verification path, ledger write path, or WS
  stream.
- **Port source only:** `../../archive/provenance/raksha-enterprise/raksha-enterprise/raksha/bus/`
  is retained for scoped tokens, rate limiting, quarantine, metrics and WS
  patterns to port later. It is not canonical and must not be imported as a
  second live bus.
- **Future target:** `packages/spine/bus.py` plus thin `apps/citizen/api.py` and
  `apps/infra/backend/api.py` adapters after Phases 2/3/8.

One canonical event envelope and one verification result will be shared by
Citizen, Infra, RAAVAN and eval harnesses.

## Consequences

**Positive**

- One signature/canonical-JSON rule.
- One quarantine rule for tampered or unsigned events.
- One seal-before-broadcast ordering.
- One WS stream for detections, proposals and decisions.

**Costs / work deferred**

- Phase 3 must reconcile the envelope, auth scopes and canonical JSON.
- Phase 8 must port enterprise HTTP/WS/metrics behaviour behind the core.
- Phase 10 must retire duplicate bus modules into provenance.

## Safety and honesty gates

- No app adapter may accept unsigned events as actionable evidence.
- No console or admin surface may override a decision from the bus path.
- No real-network containment may be exposed by the WS/API boundary.
- Phase 1 adds no code; no safety rail is relaxed.

## Verification

- Source-of-truth matrix lists exactly one current canonical bus core.
- ADR-002…ADR-008 depend on the same single verification path.
- Phase 1 exit gate: "no capability has two canonical homes" is satisfied for
  the bus by naming the spine core canonical and every other surface adapter or
  port source.
