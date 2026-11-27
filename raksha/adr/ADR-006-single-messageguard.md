# ADR-006 — One Citizen MessageGuard

> **Status:** Frozen for Phase 1 planning · Implemented for Phase 5 by [ADR-013](ADR-013-messageguard-single-source.md) · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §5, [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 5

## Context

MessageGuard exists in three places:

- `../../raksha-code/citizen/messageguard/` — the already-integrated v1 scorer, adapter, reason catalogue, normalizer, band map and en/hi/te token sets.
- `../../archive/provenance/messageguard-alternative/raksha/` (formerly `../../raksha-messageguard/raksha/`) — an alternative Part 3 package with CLI, legacy organ adapter, reasons/i18n, Hinglish corpus and extra tests; archived by Phase 5.
- `../../archive/provenance/messageguard-snapshot/raksha/` (formerly `../../random project that ew need to integrate/raksha/`) — the standalone Part 3 snapshot marked provenance-only by `INTEGRATED.md`.

The previous integration established the main-tree v1 as runtime source of
truth. Phase 1 must prevent a second detector from becoming canonical during the
combined-system consolidation.

## Decision

There is **one Citizen MessageGuard capability**.

- **Canonical home (Phase 1):** `../../raksha-code/citizen/messageguard/`.
- **Stable API:** `score_message()` remains the Citizen contract adapter;
  `analyze()` remains the measured engine. `verdict_at_least()`, band mapping,
  `evaluate_fixtures()` and `MSG-*` reason rendering stay with this package.
- **Port source:** `../../archive/provenance/messageguard-alternative/raksha/` is compared for unique
  corpus rows, legacy-adapter behaviour, CLI affordances and regression tests.
  Only unique value is ported in Phase 5.
- **Provenance only:** the standalone snapshot stays historical and is never
  imported as runtime.
- **Future target:** `apps/citizen/messageguard/` after Phase 2/5.

One corpus, one scorer, one reason catalogue, one eval result and one generated
report will exist after Phase 5.

## Consequences

**Positive**

- Citizen API compatibility is preserved.
- The 538 hand-authored fixture measurement remains reproducible and supersedes the historical 492-fixture headline.
- Real-world accuracy stays explicitly **UNMEASURED**.
- No duplicate reason-code catalogue can drift from i18n.

**Costs / work deferred**

- Phase 5 must compare corpora and tests before porting.
- Phase 5 must archive the alternative package with provenance notes.
- Phase 9 must keep all MessageGuard numbers inside the claims ledger.

## Safety and honesty gates

- No raw score is exposed to a citizen as a verdict.
- Matched scam phrases are not exposed through the explanation layer.
- No trained classifier is attempted before a consent-cleared real corpus.
- No field FPR or accuracy claim is made from hand-authored fixtures.
- Phase 1 adds no code; no safety rail is relaxed.

## Verification

- Source-of-truth matrix names one current canonical MessageGuard.
- ADR-007 names the one MessageGuard sub-runner and generated report.
- Phase 1 exit gate: "no capability has two canonical homes" is satisfied for
  MessageGuard.
