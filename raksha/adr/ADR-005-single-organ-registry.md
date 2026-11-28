> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../../docs/STATUS.md); see the [retired code note](../../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# ADR-005 — One Infra detection-organ registry

> **Status:** Frozen for Phase 1 planning · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §5, [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 6

## Context

Two 8-organ implementations exist:

- `../../raksha-code/sentinel/shields/` — four rings with the shipped physics/biology-named organs and `base_organ.py`.
- `../../archive/provenance/raksha-enterprise/raksha-enterprise/raksha/organs/` — Part 6 organ modules (`docguard`, `fileguard`, `idguard`, `netguard`, `quorumguard`, `sessionguard`, `tier0guard`, `voiceguard`) with registry and boundary tests.

The names differ, but both claim an eight-organ detection surface. Keeping both
as authorities would create two detection contracts and two fixture stories.

## Decision

There is **one Infra detection-organ capability**.

- **Canonical home (Phase 1):** `../../raksha-code/sentinel/shields/`.
- **Port source only:** `../../archive/provenance/raksha-enterprise/raksha-enterprise/raksha/organs/`
  contributes boundary tests, missing-feature behaviour and any useful fixture
  rows. It is not a second live registry.
- **Future target:** `apps/infra/detectors/` with one registry and one
  `detect(event) -> finding` contract after Phase 6.
- **Naming rule:** physics/biology names remain explanatory labels, not separate
  services and not permission to fork the contract.

## Consequences

**Positive**

- One signed telemetry path from ADR-001.
- One "missing features never flag" rule.
- One firing fixture and one silent fixture per organ.
- One per-organ measurement section in ADR-007's eval runner.

**Costs / work deferred**

- Phase 6 must map the eight shipped organs to the eight enterprise organ roles.
- Phase 6 must port useful boundary tests without importing a second registry.
- Phase 10 must retire duplicate organ packages into provenance.

## Safety and honesty gates

- Forged, unsigned or tampered events are quarantined and never detected as real.
- Absence of evidence must not produce an accusation.
- No real-network or real-host detection claim is introduced.
- The enterprise organ named `voiceguard` is **not** a Citizen VoiceGuard
  integration path; see ADR-009.
- Phase 1 adds no code; no safety rail is relaxed.

## Verification

- Source-of-truth matrix names one current canonical organ tree.
- ADR-001 supplies the single verification path.
- ADR-007 will measure the one registry, not two parallel organ suites.
