> Historical provenance: the retired voice-scorer code was removed from executable paths. Active status lives in [docs/STATUS.md](../../docs/STATUS.md); see the [retired code note](../../archive/provenance/RETIRED.md). Real-world privacy efficacy remains UNMEASURED.

# ADR-002 — One append-only evidence ledger

> **Status:** Frozen for Phase 1 planning · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Related:** [`../PHASE1_SOURCE_OF_TRUTH_MATRIX.md`](../PHASE1_SOURCE_OF_TRUTH_MATRIX.md) §5, [`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phases 3, 7 and 9

## Context

Three ledger implementations exist:

- `../../raksha-code/spine/ledger.py` with `ledger_anchor.py` and `ledger_cli.py` — current append-only SHA-256 chain and HMAC side anchor.
- `../../archive/provenance/raksha-governance/raksha-governance/raksha/ledger.py` — Part 5 reference hash chain with JSONL export.
- `../../archive/provenance/raksha-enterprise/raksha-enterprise/raksha/ledger/` — Part 6 SQLite/WAL store, pure hash chain, CLI and direct-tamper tests.

A combined system cannot allow proposals, decisions, refusals or internal guard
failures to land in different chains with different verification stories.

## Decision

There is **one evidence-ledger capability** behind one `append / verify`
interface.

- **Canonical home (Phase 1):** `../../raksha-code/spine/ledger.py`,
  `ledger_anchor.py` and `ledger_cli.py`.
- **Port sources only:** the governance reference chain and enterprise
  SQLite/WAL chain are sources for behaviour, tests and operational hardening.
  They are not independent canonical ledgers.
- **Future target:** `packages/ledger/` after Phase 3, with one CLI and one
  `GET /v1/ledger/verify`-style endpoint in Phase 8.
- **Write rule:** apps and consoles never write directly to storage. Proposals,
  allowances, refusals, escalations, forced reverts and internal failures are
  written through the one ledger service before callers see the result.

## Consequences

**Positive**

- One `verify` command detects the first bad sequence.
- One seal-before-broadcast rule.
- One place to enforce append-only semantics and admin-override refusal.
- One claims ledger can cite the same chain for demos and evals.

**Costs / work deferred**

- Phase 3 must reconcile pure-chain, SQLite/WAL and JSONL export semantics.
- Phase 7 must ensure all Governor outcomes use the one write path.
- Phase 9 must verify ledger integrity in the combined eval runner.

## Safety and honesty gates

- No historical entry may be rewritten to make a demo look cleaner.
- No admin override may create a bypass; override remains forbidden by design.
- No claim of production durability is made from fixture runs.
- Phase 1 adds no code; no safety rail is relaxed.

## Verification

- Source-of-truth matrix names exactly one current canonical ledger package.
- ADR-003 requires Governor outcomes to use this interface.
- ADR-008 keeps runtime ledger status in `../../BUILD_STATE.md`, not in planning docs.
