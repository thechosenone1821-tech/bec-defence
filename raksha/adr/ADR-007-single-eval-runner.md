# ADR-007 — One eval runner and claims ledger

> **Status:** Frozen for Phase 1 planning · MessageGuard eval runner implemented by [ADR-013](ADR-013-messageguard-single-source.md); broader Phase 9 claims ledger pending · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §5, [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 9

## Context

Evaluation and corpus generation are spread across:

- `../../raksha-code/evals/run_evals.py` and `evals/messageguard/` — current M6 table plus reproducible MessageGuard v1 results and generated docs.
- `../../raksha-code/corpora/` and `../../raksha-code/raavan/` — current corpora and sandbox replay player.
- `../../archive/provenance/raksha-enterprise/raksha-enterprise/tools/` — Part 6 deterministic corpus generator and eval runner.
- `../../archive/provenance/messageguard-alternative/raksha/raksha/evals/` and `../../archive/provenance/messageguard-snapshot/raksha/evals/` — archived alternative/standalone MessageGuard runners; not active.
- `../../raksha-code/evals/run_maya.py` — VoiceGuard eval, parked by ADR-009.

Multiple runners would produce multiple "current" tables and make honesty
labels easy to lose.

## Decision

There is **one evaluation capability**.

- **Canonical home (Phase 1):** `../../raksha-code/evals/run_evals.py` with
  `../../raksha-code/evals/messageguard/` as the current MessageGuard
  sub-runner.
- **Port / provenance sources:** enterprise tools, alternative MessageGuard
  eval packages, standalone eval scripts, corpora and RAAVAN player are merged in
  Phase 9. None is a second current authority.
- **Frozen exclusion:** `evals/run_maya.py` and all VoiceGuard eval artefacts are
  excluded until Phase 11.
- **Future target:** `evals/runners/`, `evals/corpora/`, `evals/results/` and one
  generated `docs/EVALS.md` with a claims ledger after Phase 9.
- **Drift rule:** one `run_evals --check`-style command verifies committed
  results against current code, fixtures and generated docs. Generated reports
  are never hand-edited.

## Consequences

**Positive**

- One table per capability, each with an explicit condition.
- One place to label fixture, synthetic, sandbox and real-world UNMEASURED.
- One drift check for generated docs.
- One RAAVAN replay path measured through the same verification pipeline.

**Costs / work deferred**

- Phase 9 must merge corpora without mixing synthetic and real data labels.
- Phase 9 must merge per-capability tables into one claims ledger.
- Phase 10 must add CI drift checks.

## Safety and honesty gates

- No number may appear in README, pitch or stage copy without a claims-ledger row.
- No fixture measurement may be promoted to real-world accuracy.
- No live adversary may be used by RAAVAN.
- No VoiceGuard accuracy claim enters the 10-phase runner.
- Phase 1 adds no code; no safety rail is relaxed.

## Verification

- Source-of-truth matrix names one current canonical eval runner.
- ADR-006 names the one MessageGuard measurement corpus.
- ADR-008 keeps current verified test counts in `../../BUILD_STATE.md`, not in
  planning documents.
