# RAKSHA — Roadmap

> **Last updated:** 2026-11-20 · Dates beyond Phase 0 are **targets**, not
> promises; slips are recorded in `CHANGELOG.md`, never silently edited.
> Anchor: today = 2026-11-20. Hackathon date = TBD (owner to pin).

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
- [ ] Sentinel: hospital profile graph seeded; Endpoint shield (parity-trap demo); Identity shield live on fixture auth stream
- [ ] Citizen: PWA skeleton; VoiceGuard stub returning calibrated verdicts from bundled model; MessageGuard rule+embedding v1
- [ ] Shared bus + ledger wired end-to-end with one synthetic campaign

**Day 2 — the fight**

- [ ] RAAVAN v1 running the full kill chain in the sandbox (voice → mule → phish → ransom → exfil)
- [ ] Campaign correlator fuses ≥3 weak signals across both apps into one campaign_id
- [ ] Containment planner cuts the live attack live-on-stage (dry-run): ICU stays ≥90% green
- [ ] Governor demonstration: RAAVAN attempts an ICU-VLAN cut — hard-blocked, ledger shows it
- [ ] ₹-lost-vs-₹-saved counter; attack timeline replay UI

**Day 3 — prove & rehearse**

- [ ] Eval table produced for real (baseline × metric) — measured, not adjectives
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
