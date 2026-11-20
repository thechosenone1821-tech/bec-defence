# BACKEND PART A — "Sense & Sanitize" (Planes 1 + 2)

**Owner:** Backend Developer A · **Scope:** reflexes, telemetry bus, sanitizer,
Ring-1…4 organs · **You own the microsecond path and the trust boundary.**

You do **not** touch `commander/`, `governor/`, `config/policy.yaml`, or the
UI. If you need a decision from the AI side, consume the contract
(`docs/INTERFACE_CONTRACT.md`) or run `scripts/mock_plane_b.py`.

---

## 0. Setup (10 minutes)

```bash
cd eigenshield-v2
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                       # everything green before you change anything
python simulator/demo_01_bec_and_cookie.py
```

Python 3.10+ required (tested on 3.11/3.12). No GPU. No internet at runtime.

## 1. What you own

| Area | Files | Notes |
| --- | --- | --- |
| Base organ | `reflexes/base_organ.py` | telemetry emitter + **signed RPC** (HMAC) receiver |
| Ring 1 | `reflexes/ring1_perimeter_identity/{bec_spectral_filter.py, cookie_fluid_turbulence.py}` | Organ 1 BEC projector · Organ 2 Cookie killer |
| Ring 2 | `reflexes/ring2_ai_defense/{bragg_fft_firewall.py, hessian_lyapunov_guard.py}` | Organ 3 Bragg gate · Organ 4 Lyapunov guard |
| Ring 3 | `reflexes/ring3_endpoint_silicon/{page_curve_trap.py, landauer_thermal_audit.py}` | Organ 5 Page-Curve honey-blocks · Organ 6 Landauer auditor |
| Ring 4 | `reflexes/ring4_network_healing/{hashimoto_percolation.py, muts_ebpf_repair.py}` | Organ 7 Hashimoto min-cut · Organ 8 MutS/MutL splice |
| Bus | `bus/sanitizer.py`, `bus/entity_graph.py`, `bus/event_server.py` | ingest → sanitize → buffer → WS |
| Topology | `config/company_topology.json` | VLAN/host/user graph for Ring-4 + tests |
| Stage acts | `simulator/demo_01..04_*.py` | Ring 1–4 acts |
| Mocks | `scripts/mock_plane_b.py` | fake Governor/Commander for your dev loop |
| Tests | `tests/test_organs.py`, `test_page_curve.py`, `test_hashimoto.py`, `test_sanitizer.py` | your regression net |

## 2. Engineering notes per organ

1. **BEC Spectral Projector** — SVD on the *mean-centered* (NOT z-scored)
   behavioral matrix; `R = σ₁²/Σσᵢ²` (k=5). On `R > 0.72`, split the
   projection onto `v1` at 0 and excise the **tighter** side (it's the
   condensed botnet). Do not re-add per-feature scaling — it erases the
   variance-concentration signal. Demo trigger: `demo_01` (R ≈ 0.77).
2. **Cookie Turbulence** — `Re_beh = 1000·ρ·(v/1000)·(L/500)/μ`. Laminar <
   1380, turbulent ≥ 2300. Users calibrate via `calibrate_baseline()`.
   Injection of replay ⇒ revoke + FIDO2. Keep the pipe-flow analogy honest:
   it's a behavioral analog, not literal fluid dynamics.
3. **Bragg FFT Firewall** — hashing-projected token embeddings (dim 64);
   FFT peak ratio catches periodic adversarial suffixes; Fiedler λ₂ of the
   kNN token graph catches connectivity fracture. Thresholds (0.32 / 0.05)
   are demo calibration — expose them as constructor args; do not hard-code
   new magic numbers without a test.
4. **Hessian–Lyapunov Guard** — finite-difference jerk proxy
   `κ = (a·v)/‖v‖²`, restore along `−sign(κ)·v` when `|κ| > 2.5`. This is **not**
   true second-order geometry — keep the module docstring disclaimer intact.
5. **Page-Curve Trap** — 4 KB honey pairs, `P = A ⊕ H(B, salt)` via SHA-256
   keystream. `on_write()` breaks ⇒ `PID_TERMINATED` **decision**; actual
   `os.kill` only with `allow_real_kill=True` and only ever in the sandbox
   (`demo_03 --sandbox`). Default dry-run. Never SIGKILL anything from the
   telemetry bus.
6. **Landauer Auditor** — linear observer `P ≈ a·IPC + b·T_die + c` fit on
   ≥ 10 benign samples; sustained residual > 8 W (5 samples) ⇒
   `UNACCOUNTED_POWER_RESIDUAL`. Real RAPL/WMI hooks are out of scope for
   the MVP; keep the interface so real sensors drop in later.
7. **Hashimoto Percolation** — **read the module docstring first.** For
   finite graphs ρ(B)=0 on forests and ≥ 1 once any cycle remains — the
   spec's 0.90 target is aspirational (`target_met`), never a reason to cut
   Tier-0 edges or breach the critical-uptime floor. Greedy cheapest-first
   min cut; crown edges (weight ∞) are never candidates. Demo: 5 surgical
   cuts, 100 % mission/crown load preserved.
8. **MutS/MutL Repair** — simulated eBPF/LSM with the real control surface
   (`register_invariant → report_mismatch → freeze → splice ≤ 50 ms`).
   Real kernel hooks need CAP_BPF/CAP_SYS_ADMIN; the simulation preserves the
   decision flow and latency accounting, not the kernel mechanism.

## 3. The trust boundary is your reputation

`bus/sanitizer.py` must uphold, property-test style:

* No raw string ever appears in the output (`tests/test_sanitizer.py`
  encodes this; extend it with your own fuzz cases).
* Severity always clamped to [0,1]; unknown metrics keys dropped wholesale;
  string metric values become `sha256:` digests.
* Token stability: same input + salt ⇒ same token (env `EIGENSHIELD_SALT`).

If the Commander ever sees a raw filename or prompt — even mangled — that's
a P0 bug. Fix at the sanitizer, never by filtering in the orchestrator.

## 4. Your dev loop against B (no waiting on B)

```bash
# terminal 1 — the real bus + your organs
python -m bus.event_server --policy config/policy.yaml --topology config/company_topology.json --port 8080

# terminal 2 — feed synthetic Plane-1 traffic and watch WS frames
python scripts/mock_plane_b.py --help    # mock Governor/Commander shapes
python scripts/mock_plane_a.py | head    # shapes B feeds you back

# or curl end-to-end smoke
curl -s -X POST localhost:8080/api/ingest -H 'Content-Type: application/json' \
  -d "$(python scripts/mock_plane_a.py | head -1)"
curl -s localhost:8080/api/state | jq
```

`mock_plane_b.py` consumes sanitized events on stdin and prints the plan +
decision objects B will produce — use it in your unit tests instead of
importing `commander/` (keeps the seam clean).

## 5. Acceptance criteria (M1–M4)

M1 — `pytest -q` green from a clean clone; `demo_01..04` exit 0; BEC ratio
0.72+ on the demo corpus; Page-Curve kills its first 4 KB write in < 1 ms
(dry-run); Percolation plan preserves ≥ 90 % critical weight with tier-0
untouched.

M2 — Sanitizer fuzz: 50 adversarial strings (unicode, RTL, SQL-ish, shell-ish,
100 KB payloads) → zero raw leakage; WS client reconnects without server
change; `/api/state` returns within 50 ms @ 500 buffered events.

M3 — ACT 1–4 rehearsed end-to-end twice consecutively without crash; latency
printouts show < 2 ms reflex path on stage hardware; fallback_rules commander
(SLM killed) still produces sensible plans downstream of your events.

M4 — Profiled SVD on 50k-session windows (numpy, no GPU); docs touch-ups;
handoff notes for UI/UX (feed shapes they can rely on).

## 6. Watch-outs

* Don't SIGKILL in demos except against your own sandbox child PID.
* Keep `BaseOrgan.emit()` dumb — no networking inside organs.
* `EntityGraph` is in-memory and unbounded in `add_event` rate — bound the
  ingest surface at the API layer if you add batch ingest.
* If you bump `/api/state` shape, bump `CONTRACT_VERSION` (see contract) and
  tell B and UI/UX **before** merge.
* Ring 4 organ 8 in the demo is a *simulation*; keep claims precise in
  comments/docs — enterprise buyers' engineers will read them.

## 7. Definition of done

`pytest tests/test_organs.py tests/test_page_curve.py tests/test_hashimoto.py tests/test_sanitizer.py -q`
→ all green; four stage demos exit 0; contract fixtures updated if (and only
if) formats changed with B sign-off; `docs/` updated.

---

## v2.1 addendum (FORTRESS) — what Part A must emit now

* **Every event the organs hand to Part B must carry a `mac`** — see
  `fortress/telemetry_mac.py`. `scripts/mock_plane_a.py` already does this
  (`--unsigned` simulates the attack). If your organs bypass `mock_plane_a`,
  import `sign_event` and sign at emission time.
* Keys: organs get `EIGENSHIELD_BUS_KEY`; the bus holds the same key to verify.
  Never ship the key inside code or artifacts.
* Unsigned organ output is *accepted for visibility but never acted on* — a
  signed-but-garbage organ is bounded by the Governor's budgets, so signing is
  necessary, not sufficient.
* `sys.path` tip: run scripts from the `eigenshield-v2/` root or rely on the
  `sys.path.insert` prelude the mocks use; otherwise `fortress` will not import.
