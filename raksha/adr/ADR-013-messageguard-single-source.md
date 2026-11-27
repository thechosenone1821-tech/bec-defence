# ADR-013 — One MessageGuard scorer and one measurement corpus

> **Status:** Accepted for Phase 5 code scaffold · **Date:** 2026-11-26
> **Decision owner:** repo maintainer (human) · **Recorded by:** AI-assisted maintainer session
> **Supersedes / implements:** the Phase 5 work planned in [ADR-006](ADR-006-single-messageguard.md); related to [ADR-007](ADR-007-single-eval-runner.md), [ADR-011](ADR-011-unified-contracts.md) and [ADR-012](ADR-012-citizen-consolidation.md)
> **Branch:** `arena/3b136fd9-bec-defence`

## Context

Before Phase 5, `apps/citizen/messageguard/` was the integrated runtime v1
scorer, but the repository still contained an independent Part 3 package under
`raksha-messageguard/raksha/` with `assess()` / `SignalFamilyScorer`, `msg.*`
reason codes, its own CLI, legacy organ adapter, 431-row corpus, Hinglish
fixtures, eval results and tests. A second standalone snapshot under
`random project that ew need to integrate/raksha/` duplicated the 492-row
fixture corpus and was already marked provenance-only by `INTEGRATED.md`.
[`../COMBINED_SYSTEM_ROADMAP.md`](../COMBINED_SYSTEM_ROADMAP.md) Phase 5
required one corpus, one generated eval document, one reason catalogue and one
detector interface, with the alternative tree archived with provenance.

The maintainer's standing constraint is **no AI models**: no LLM, Commander,
SLM/Ollama, MAYA or VoiceGuard model endpoint, no inference and no
model-dependent test run. Phase 5 is code/docs/corpus consolidation only;
Phase 6+, app-root merging and VoiceGuard/MAYA integration remain out of scope.

## Decision

There is **one Citizen MessageGuard capability**.

- **Canonical detector:** `apps/citizen/messageguard/`. `analyze()` is the
  measured scorer; `score_message()` is the Citizen API adapter. The package
  now also owns `detect_language()`, the ported legacy organ adapter and a
  sanitized operator CLI. `SUPPORTED_LANGS` is
  `("auto", "en", "hi", "te", "hinglish")`.
- **Compatibility aliases:** `citizen.messageguard` and
  `raksha-code/apps/citizen/messageguard` resolve to the same canonical files.
  They are not a second scorer.
- **One corpus:** `raksha-code/citizen/fixtures/messageguard/` with 538
  hand-authored / in-distribution rows: 402 scam, 136 benign, including 46
  unique Hinglish rows ported from the alternative package. The other 385
  alternative en/hi/te rows are not ported.
- **One eval:** `raksha-code/evals/messageguard/run_evals.py` writes
  `results.json`; `gen_evals_md.py` writes the one generated
  `raksha/MESSAGEGUARD_EVALS.md`. en/hi/te use `lang="auto"` as before;
  Hinglish uses explicit `lang="hinglish"`. `run_evals.py --check` is the one
  drift command.
- **One reason catalogue:** `packages/contracts/reasons.py` owns the `MSG-*`
  codes. Hinglish token rows reuse those codes; the alternative `msg.*`
  catalogue is retired. Citizen explanations still render through
  `packages/contracts/i18n.py` and `apps/citizen/copy.py`.
- **Provenance only:** the alternative package and standalone snapshot are
  moved under `archive/provenance/`. Their `messageguard` package directories
  are renamed `messageguard_legacy`, and their tests are ignored by
  `archive/provenance/conftest.py` and the no-AI runner. No archived module is
  a runtime import.

## Consequences

**Positive**

- One detector interface, one corpus, one generated eval document and one
  reason catalogue.
- The published en/hi/te per-language aggregates are unchanged; the overall
  numbers are regenerated only because the one corpus grew by 46 unique
  hand-authored Hinglish rows.
- Hinglish negation/FP regressions, legacy-adapter behaviour and CLI
  affordances are ported without porting a second scorer.
- Real-world accuracy stays explicitly **UNMEASURED**; every published number
  is labelled hand-authored / in-distribution.

**Costs / work deferred**

- The long tail of Latin transliteration remains unmeasured and unclaimed.
- Sender-ID allowlisting and consent-cleared device corpora remain future
  app-layer work; the message-only detector still cannot resolve senders or
  fetch URLs.
- Phase 9 still owns the broader claims ledger and eval-runner consolidation.
- Phase 11 still owns VoiceGuard/MAYA; no frozen asset was edited.

## Safety and honesty gates

- No AI model inference or model endpoint of any kind.
- No raw score to citizens, no `SAFE` verdict, no PII forwarding, no matched
  scam phrases in citizen copy.
- No clone, field, real-network or real-world accuracy claim.
- No weakened signature/Governor requirement; no real containment.
- No commit or push was performed as part of this scaffold.

## Verification

- `tools/check_phase5_messageguard.py` proves one importable scorer, one
  catalogue, one corpus, one `results.json`, one generated doc and archived
  provenance markers.
- `run_evals.py --check` reproduces the committed numbers.
- `tools/run_phase4_pytest.py` collects one active MessageGuard suite and
  ignores the archived provenance tests; the no-AI plugin reports no model
  module loaded.
- The generated eval document is byte-for-byte reproducible from
  `gen_evals_md.py`.
- `tools/check_phase4_citizen.py`, `tools/check_phase3_contracts.py`,
  `tools/check_local_links.py` and `tools/check_frozen_assets.py` remain green.

Implementation details are in
[`../PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](../PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md).
