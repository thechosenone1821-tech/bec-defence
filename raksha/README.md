# RAKSHA — The Immune System for Digital India

> **Status:** Building — **M1 spine · M2 Sentinel shields · M3 Citizen PWA ·
> M4 RAAVAN kill chain + cross-app campaign fusion · M5 containment planner +
> Governor floor** shipped in `../raksha-code/` (67/67 green; organ-backed
> executor; heuristic citizen detectors — demo-grade by design).
> Sentinel → Citizen → RAAVAN → containment ✓.
> **Last updated:** 2026-11-20 · **Version:** docs v0.6.0
> **Tagline:** *"We built Raksha. We sicked a ten-headed AI attacker on it. Live on stage."*

RAKSHA is an AI-native, cross-layer cyber-defence ecosystem for India, built as
**two applications sharing one defensive doctrine**:

| App | Protects | What it is |
| --- | --- | --- |
| **RAKSHA Citizen** | Ordinary people, on their phones | Voice-clone call screening, multilingual scam-message defence (UPI collect-request / KYC / "digital arrest" scripts), one-tap incident reporting feeding the shared attack graph |
| **RAKSHA Sentinel** | Critical infrastructure estates | Cross-layer detection & response for hospitals, payment platforms, identity, cloud & AI agents — with **counterfactual minimum-disruption containment** instead of "shut everything down" |

Both ship against **RAAVAN** — a controlled AI red-team adversary (ten attack
techniques) used only inside sandboxes and stage demos to prove the defence.

## Why this exists

Read [`PROBLEM_STATEMENT.md`](PROBLEM_STATEMENT.md) — the short version is
that India's citizens and critical systems are being attacked by AI-driven
campaigns, and current defences are fragmented, human-speed, and binary
("blocked" or "everything shut down"). RAKSHA exists to cut the attacker —
never the innocent infrastructure around them.

## Document map

| File | Read it if you are… |
| --- | --- |
| [`PROBLEM_STATEMENT.md`](PROBLEM_STATEMENT.md) | anyone — the formal (advisory) + spoken (90-second) statement of the problem |
| [`CONTEXT.md`](CONTEXT.md) | an AI or new engineer — full project context, lineage, principles, glossary, verified-facts discipline |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | building anything — the two apps, shared spine, module map |
| [`ROADMAP.md`](ROADMAP.md) | planning — phases, milestones, hackathon sprint plan |
| [`BUILD_GUIDE.md`](BUILD_GUIDE.md) | writing code — what to build, in what order, how, with safety rules |
| [`AI_HANDOFF.md`](AI_HANDOFF.md) | an AI agent working here — mandatory read; rules, status, update protocol |
| [`CHANGELOG.md`](CHANGELOG.md) | tracking change — living log of doc/code milestones |

## Rules of the road (non-negotiable)

1. **Honesty in writing.** Never print an unverified statistic as fact. Tag
   it `[VERIFY]` and link the source. See `CONTEXT.md §5`.
2. **Fail closed, always.** No defensive action without policy clearance;
   Tier-0 / ICU-class cuts are impossible by construction, not by convention.
3. **Dry-run by default.** Nothing in this repo launches real attacks, real
   exfiltration, or real network traffic against real systems.
4. **One doctrine, two apps.** Citizen and Sentinel stay on one shared spine
   (attack graph + evidence ledger + Governor). Divergence needs a written
   decision in `CHANGELOG.md`.
5. **These docs are living.** After any substantive change, bump the
   *Last updated* line, add a `CHANGELOG.md` entry, and fix contradictions —
   don't leave stale docs for the next agent.

## Repo lineage

This repository already carries **EIGENSHIELD v2.0 → v2.1 FORTRESS**
(`../eigenshield-v2/`), a working 4-plane reference defence build (8 organs,
Governor, hash-chained ledger, N-version TCB). RAKSHA **inherits and
generalizes it**: the Governor becomes Sentinel's safety brain; the reflex
organs become schedulable detectors; the FORTRESS layer becomes
infrastructure non-negotiables (signed evidence, no single point of trust).
See `CONTEXT.md §3` for the port map.

## License

MIT (inherited from repo root). RAKSHA will be released open source — the
promise made on stage stays open.
