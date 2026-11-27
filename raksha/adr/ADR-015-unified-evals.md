# ADR-015 — one deterministic eval runner, claims ledger and drift check

**Status:** Accepted / implemented in Phase 9
**Date:** 2026-11-26
**Scope:** Citizen, MessageGuard, organs, governance, end-to-end replay

## Decision

There is exactly one measurement path:

- `evals/corpus.py` generates the committed deterministic corpus.
- `evals/replay.py` is the only end-to-end sandbox replay player.
- `evals/run_evals.py` is the only eval runner and drift check.
- `EVALS.md` is the only generated evaluation document.
- `evals/claims_ledger.json` is the only claims ledger; hand-authored outward
  documentation rows come from `evals/claims_sources.json`.
- `evals/messageguard.py` owns the one MessageGuard computation; all legacy
  `run_evals.py` / `gen_evals_md.py` paths are thin compatibility wrappers or
  provenance.

Every number in a README, status page, changelog, pitch or evaluation document
must carry a condition — fixture / synthetic / sandbox / hand-authored /
real-world UNMEASURED — and a source row. Real-world accuracy, latency, uptime,
recall and false-positive rate remain UNMEASURED. Generated eval documents are
never hand-edited; `make eval` / `run_evals --check` proves they match the
committed results.

## Consequences

- Historical M6 baseline tables, enterprise RAAVAN players, alternative
  MessageGuard eval trees and standalone corpora generators are provenance, not
  active measurement sources.
- VoiceGuard / MAYA evals are excluded. They may re-enter only through the
  future Phase 11 gate in `docs/STATUS.md`.
- No model, Commander, SLM/Ollama endpoint, live executor or network service is
  used by the runner. Dry-run remains the only executor mode.
- The claims-ledger checker fails any new outward number that lacks a
  hand-authored source row or any generated number that lacks a result pointer.

## Validation

`python -m evals.run_evals --check` is green for Citizen, MessageGuard, organs,
governance and end-to-end replay. `tools/check_claims_ledger.py` verifies the
ledger, static documentation numbers, real-world claim wording and VoiceGuard
exclusion. `tools/check_eval_drift.py` is the single CI drift gate.

See [`../PHASE910_UNIFIED_RELEASE.md`](../PHASE910_UNIFIED_RELEASE.md) and
[`../../docs/STATUS.md`](../../docs/STATUS.md).
