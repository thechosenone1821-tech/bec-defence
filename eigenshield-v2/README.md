# EIGENSHIELD v2.1 — Company-Wide Autonomous Immune System (reference build)

> **v2.1 FORTRESS** — the v2.0 four-plane build, hardened so that no *single*
> compromise (hijacked AI, forged telemetry, tampered config, re-forged ledger,
> one buggy decision implementation) can reach the crown jewels. Fails closed,
> everywhere. See **[`docs/FORTRESS.md`](docs/FORTRESS.md)** for the threat model,
> control matrix, evidence and honest limits.

Eight physics- and biology-inspired defense organs in four paired reflex rings,
an orchestrating local Small AI Commander, and a deterministic zero-AI Hard
Safety Governor — implemented as a runnable, test-covered reference for the
hackathon spec in the repository-root `README.md`, with the v2.1 FORTRESS
resilience layer from the repo-root brief ("even if the core is compromised,
it must not be hacked").

> **Status honesty (read this first).** This is a *stage-grade reference
> implementation*, not production security software. Plane 1 math is real
> (SVD, FFT, non-backtracking spectra, parity hashing). Organ 8 simulates the
> eBPF/LSM shield with the same control surface (register → mismatch → freeze
> → splice) but not the kernel mechanism — that needs `CAP_BPF` and is out of
> scope. Organ 6 consumes RAPL/WMI-class power telemetry through a calibrated
> observer; on commodity machines you feed it synthetic or sensor-backed
> streams. Plane 3 runs 100 % offline against a local Ollama model, and
> degrades to a deterministic rule-based commander when no model is present.
> Everything else — sanitizer, governor, ledger, watchdog, demos — is real.

## Quickstart

```bash
cd eigenshield-v2
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 0) boot-time config integrity check (optional now, mandatory in CI)
python -m fortress.boot_manifest --check config/manifest.json   # exit 2 ⇒ refuse to boot

# 1) run the whole test suite (34 tests)
pytest -q

# 2) run the 5-act stage demo (Rings 1–4 + Governor)
python simulator/demo_01_bec_and_cookie.py
python simulator/demo_02_bragg_and_lyapunov.py            # add --interactive for judges
python simulator/demo_03_ransomware_and_rootkit.py --sandbox ./tmp_demo_files
python simulator/demo_04_percolation_and_muts.py
python simulator/demo_05_governor_hallucination.py
python simulator/demo_06_fortress_breach_drill.py      # ACT 6 — 6 breach drills, all must fail closed

# 3) boot the telemetry bus + integrated pipeline (planes 3/4 wired in-process)
python -m bus.event_server --policy config/policy.yaml \
    --topology config/company_topology.json --model qwen3.5:4b --port 8080

curl -s localhost:8080/api/health
curl -s -X POST localhost:8080/api/ingest -H 'Content-Type: application/json' \
     -d @<(python scripts/mock_plane_a.py | head -1)   # one synthetic event
curl -s -X POST localhost:8080/api/orchestrate         # full correlation + Governor pass
```

Optional, for the real local model (Plane 3): `ollama pull qwen3.5:4b` then
`curl localhost:11434/api/tags`. Without it everything still works via
`commander_mode: "fallback_rules"` — by design.

## What's inside

```text
reflexes/     PLANE 1 — 4 paired reflex rings (8 organs), microsecond math
bus/          PLANE 2 — zero-trust sanitizer, 10-min entity graph, FastAPI+WS broker
commander/    PLANE 3 — local SLM client (Ollama), kill-chain orchestrator, 10-tool allowlist
governor/     PLANE 4 — schema lock · crown-jewel lock · blast-radius budgeter ·
              human step-up gate · 15 s rollback watchdog · SHA-256 audit ledger
fortress/     v2.1 RESILIENCE — N-version TCB decision twins · HMAC-signed telemetry ·
              replay defense · canary tripwires · anti-probing AI freeze ·
              config boot-pinning · ledger tail anchor · subprocess sandbox
simulator/    5-act stage demos (POLLUTION-free, sandboxed, dry-run safe)
config/       policy.yaml (crown jewels, budgets) + company_topology.json (9 VLANs)
docs/         WORK_SPLIT.md · BACKEND_PART_A.md · BACKEND_PART_B.md ·
              INTERFACE_CONTRACT.md (v1.0.0 + v2.1 addendum) · UI_UX_BRIEF.md ·
              FORTRESS.md
tests/        34 pytest regression tests (sanitizer fuzz, governor invariants,
              ledger tamper + anchor, percolation correctness, rank-1 detection,
              exhaustive TCB invariant sweep, canary/tripwire/manifest)
scripts/      mock_plane_a.py / mock_plane_b.py — develop either half independently
dashboard/    intentionally empty — owned by the UI/UX team (see its README)
```

## How this repository is built by 2–3 people

Two backend developers own disjoint halves split at the trust boundary; a
UI/UX team owns the dashboard. Read **[`docs/WORK_SPLIT.md`](docs/WORK_SPLIT.md)**
first — it has the file-level ownership map, milestones and rules of
engagement. The short version:

| Part | Owner | Planes | Boundary |
| --- | --- | --- | --- |
| `BACKEND_PART_A.md` — "Sense & Sanitize" | Backend dev 1 | 1 + 2 | emits sanitized events |
| `BACKEND_PART_B.md` — "Decide & Contain" | Backend dev 2 | 3 + 4 | consumes events, disposes via Governor |
| `UI_UX_BRIEF.md` — SOC dashboard | UI/UX team | view layer | consumes REST + WS only |

The frozen A⇄B⇄UI contract lives in **[`docs/INTERFACE_CONTRACT.md`](docs/INTERFACE_CONTRACT.md)**.

## Engineering transparency (known limits)

* **Finite-graph percolation.** ρ(B) < 1 is impossible while any cycle remains;
  crown-jewel clinical triangles pin ρ(B) = 1.0 *by design*. The containment
  engine therefore targets **criticality** (ρ ≤ 1) subject to a 90 %
  mission-critical uptime floor and *never* cuts Tier-0 edges.
  (`reflexes/ring4_network_healing/hashimoto_percolation.py`)
* **Hessian–Lyapunov guard** uses a finite-difference jerk proxy for κ, not true
  second-order loss geometry — honest approximation, documented in code.
* **Landauer organ** audits macroscopic power-vs-IPC residuals, since
  single-bit Landauer dissipation is below ambient noise.
* **Sanitizer salt**: set `EIGENSHIELD_SALT` in real deployments
  (dev default is documented in `bus/sanitizer.py`).
* **Self-defense**: Plane 1 runs fully autonomously if the Commander crashes;
  the Governor enforces Tier-0 guarantees regardless of what any AI proposes.
* **FORTRESS (v2.1)**: organ-signed telemetry is mandatory for AI action — the
  Commander never sees unsigned events; any TCB disagreement, canary hit or
  probing burst freezes the AI path until a human reopens it; config and
  ledger integrity are pinned and cross-checked. Honest limits are documented
  in `docs/FORTRESS.md` — in particular the in-process HMAC is an integrity
  tag, not a process boundary; production deployments also need mTLS, a
  separate UID/HSM for keys, and WORM/notarized ledger storage.
* **Ledger**: `audit_ledger.jsonl` is written to the working directory by the
  bus (git-ignored); in containers it lives on the `eigenshield-ledger` volume.

## Stage demo one-liners (for the keynote)

```bash
python simulator/demo_01_bec_and_cookie.py      # ACT 1 — Ring 1: bots excised in ~1 ms
python simulator/demo_02_bragg_and_lyapunov.py  # ACT 2 — Ring 2: injection blocked, jailbreak snapped back
python simulator/demo_03_ransomware_and_rootkit.py --sandbox ./tmp_demo_files
                                                # ACT 3 — Ring 3: PID dies on the first 4 KB
python simulator/demo_04_percolation_and_muts.py# ACT 4 — Ring 4: worm boxed, 2nd exploit fails in ms
python simulator/demo_05_governor_hallucination.py
python simulator/demo_06_fortress_breach_drill.py      # ACT 6 — 6 breach drills, all must fail closed
                                                # ACT 5 — Plane 4: AI hallucination hard-blocked; ICU online
```

## License

MIT (inherits repo root). Root-level legacy PoC (`../bec-defence/`,
`spectral-defence-poc`) is kept for reference; this directory supersedes it.
