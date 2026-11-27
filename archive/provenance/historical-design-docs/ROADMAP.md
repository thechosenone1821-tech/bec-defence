# RAKSHA — Roadmap

> **Last updated:** 2026-11-26 · Dates beyond Phase 0 are **targets**, not
> promises; slips are recorded in `CHANGELOG.md`, never silently edited.
> Anchor: original plan written 2026-11-20; current verified state is in
> `../BUILD_STATE.md`. Hackathon date = TBD (owner to pin).
>
> **Phase 1 note:** this is the historical hackathon build roadmap. The
> combined-system 10-phase plan is
> [`COMBINED_SYSTEM_ROADMAP.md`](../../../raksha/COMBINED_SYSTEM_ROADMAP.md); its docs-only
> Phase 1 freeze is [`PHASE1_ARCHITECTURE_FREEZE.md`](../../../raksha/PHASE1_ARCHITECTURE_FREEZE.md).
> Do not read the hackathon "Phase 1" below as the combined-system Phase 1.

---

## Phase 0 — Documentation & spec lock (NOW → +1 week)

| # | Milestone | Exit criteria |
|---|---|---|
| 0.1 | Context pack (this directory) | AI-readable; verified-facts discipline in place ✅ (v0.1.0) |
| 0.2 | Problem statement frozen after maintainer review | Part I/II approved; [VERIFY] items resolved or struck |
| 0.3 | RAAVAN playbook v1 written | `raavan/playbook.yaml`, 10 techniques, each with fixture + expected defense |
| 0.4 | Eval harness spec frozen | Baselines, metrics, seeded scenarios defined |
| 0.5 | Pilot letter draft (one district hospital + one campus) | Unsigned OK; needed for "critical infrastructure" wording |

## Phase 1 — Hackathon build (target: 72-hour sprint, date TBD)

**Day 1 — foundations**

- [x] Repo layout per `BUILD_GUIDE.md` §2; shared packages extracted from eigenshield-v2 (spine ported: sanitizer, ledger, Governor, TCB, tripwire, bus) — M1 DONE, 27/27 tests green
- [x] Sentinel: shields ported (all 8 organs from eigenshield-v2), organ-backed executor, tests 37/37 green — hospital-profile graph seeding is the remaining Day-1 item
- [x] Citizen: PWA shipped (vanilla JS, offline SW, 1930 panic button); MessageGuard v1 integrated (deterministic en/hi/te/hinglish rules, 538 hand-authored fixtures, measured FP review — real-world UNMEASURED); VoiceGuard = synthetic-corpus screening, never claims clone detection; report rail signed+forwarded — Phase 5 deterministic checks recorded in `../BUILD_STATE.md` as of 2026-11-26
- [ ] Shared bus + ledger wired end-to-end with one synthetic campaign

**Day 2 — the fight**

- [x] RAAVAN v1 running the full kill chain in the sandbox (voice → invoice → replay → ransom) — live `cmp_*` fusion across citizen + infra legs; forged probes held closed; ICU-cut counterattack hard-blocked
- [ ] Campaign correlator fuses ≥3 weak signals across both apps into one campaign_id
- [x] Containment planner cuts the live attack live-on-stage (dry-run): ingress cut preserves 100% critical weight, ICU INTACT; deep-implant cut below Governor 90% floor correctly BLOCKED for human step-up
- [ ] Governor demonstration: RAAVAN attempts an ICU-VLAN cut — hard-blocked, ledger shows it
- [ ] ₹-lost-vs-₹-saved counter; attack timeline replay UI

**Day 3 — prove & rehearse**

- [x] Eval table produced for real (baseline × metric) — measured, not adjectives (raksha/EVALS.md; stage rehearsal is human, see M6 checklist)
- [ ] Stage run-through ×5; every [VERIFY] stat checked the night before
- [ ] Backup video of the full Act-2 sequence — in case the Wi-Fi dies
- [ ] Judges'-turn script ("add your attack to RAAVAN") with canned safe inputs
- [ ] Post-demo: docs updated to v0.2.0 with what actually got built

## Phase 2 — Hardening (hackathon + 2–6 weeks)

- Signed-OTA updates for Citizen app; on-device model quantization v1
- Sentinel: real agent integration (eBPF/LSM dry-run verified), RBAC, admin console
- Evidence ledger notarization (WORM or transparency-log mirror)
- Security review pass; SBOM; dependency pinning
- Multilingual reach: hi / te / en message corpus; voice-clone eval on Indian-accented synthetic speech

## Phase 3 — Pilot (hackathon + 1–3 months)

- **Pilot A:** one district hospital (IT-VLAN monitoring, ICU protection, zero PHI retention, written MoU)
- **Pilot B:** university campus or cooperative payment/fraud team (citizen-side signals)
- Threat-led tabletop with the pilot's IT generalist; measure false-positive rate in vivo
- Legal review of data flows (1930 helpline linkage; DPDP Act alignment)

## Phase 4 — Public release (hackathon + 3–6 months)

- Open-source release under MIT; reference deployment documented
- Audited threat model; red-team report published
- Vision: every district hospital and school gets the stack free — the promise on stage kept

## Release train

| Tag | Meaning |
| --- | --- |
| v0.1.0 (now) | Docs complete, nothing built |
| v0.2.0 | Hackathon MVP — two apps demoable, dry-run only |
| v0.3.0 | Hardened beta — pilots invited |
| v0.4.0 | Pilot-proven — public source release |

## Slippage & course-correction

If a milestone slips >2 weeks: update this file with dates + one-line reason,
add a `CHANGELOG.md` entry, and state the cut made (scope is negotiable,
safety is not — Governor, ledger, dry-run never get cut).

## Integration status note (2026-11-26)

Phases 6–8 of the combined-system roadmap are implemented with one detector
registry, one deterministic safety brain, one runtime/ledger path and one
read-only Infra console. See
[`PHASE678_UNIFIED_INTEGRATION.md`](../../../raksha/PHASE678_UNIFIED_INTEGRATION.md). Phase 9/10
remain future work; VoiceGuard/MAYA remain frozen.
