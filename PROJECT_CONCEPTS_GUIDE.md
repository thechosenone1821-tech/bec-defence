# RAKSHA — the whole project, explained

A learning document, not a pitch. It assumes you have the repository open and it
points at the file that owns each idea. Read it once end to end and you can
answer most questions a technical audience asks after the demo; the five
exercises at the end are the fastest way to *really* learn it.

## 1. The shape of it

RAKSHA is **one defence spine with two operators**. A Citizen app protects a
person on a phone; an Infrastructure app protects the enterprise the person is
being lured into. They are not two products glued together — they share one
event contract, one verification path, one governance layer and one ledger, so a
consumer-side signal and a network-side signal can fuse into a single campaign.

```
apps/citizen/      the person side: MessageGuard screen, risk fusion, signed
                   reports, the VIGIL image-privacy runtime, offline PWA
apps/infra/        the enterprise side: detector registry, quarantine, campaign
                   fusion, Governor, dry-run executor, console APIs, demos
packages/contracts the shared envelope: profiles, HMAC, canonical JSON
packages/spine     the runtime: ingest, rate limiting, fusion, ledger wiring
packages/governance the Governor + the only executor (dry-run)
packages/ledger    the append-only hash-chained record and its CLI
packages/frontend  the gateway that lets one browser origin talk to both apps
frontend/          the Next.js console ("Phosphor") that both apps serve
tools/             the gates: integration checkers, HTTP smokes, claims, links
evals/             the one measurement path that generates EVALS.md
docs/ STATUS.md    the honest current-state page
raksha-code/       compatibility aliases so historical import paths still resolve
```

Two apps, exactly. There is **no database, no message broker, no queue and no
external service** — the ledger is an in-process append-only chain, which is why
the whole thing boots from a cold shell in about four seconds and why it can run
on a plane. There is deliberately no third service: the launcher and the release
gate both assert it.

## 2. The contract: how an "event" is defined

Everything in the enterprise half is an **event**, and everything about an event
is specified in `packages/contracts/envelope.py`.

* Contract version `raksha-event-v1`.
* Three envelope **profiles** are accepted and normalised identically, because
  real estates have legacy senders: `organ-telemetry-v1` (a `mac` field),
  `organ-sealed-v1` (`mac` + `signature`), and `enterprise-i1-v1` (`sig` +
  `sig_alg`). The **I1** shape is the one the demos and the console use, and its
  required fields are the vocabulary of the whole product:
  `event_id`, `ts`, `organ`, `campaign_id`, `case_id`, `leg`, `severity`,
  `entity`, `summary`, `payload` — with `leg` restricted to `citizen` or
  `infra`. That is what "cross-leg fusion" means: two events, one citizen-side
  and one infra-side, under the same `campaign_id`.
* Signature algorithm is `HMAC-SHA256`; the signed bytes are the **canonical
  JSON** form (`json.dumps(..., sort_keys=True, separators=(',', ':'),
  ensure_ascii=True)`). Key ordering can never change a signature, so any
  language can produce a byte-identical signing body. That single decision is
  what makes the ledger verifiable across components.
* **Verification and gating are both required.** A valid signature alone does not
  make an event actionable; a Governor decision does. Conversely a Governor
  decision can never be reached by an unverified event.

## 3. The pipeline, in order

This is the one thing to memorise. `packages/spine/runtime.py` runs it:

1. **Ingest** (`POST /api/ingest`, one event per call) or the signed batch path
   `POST /api/gateway/spine-signed` used by the browser.
2. **Structural validation** — the required I1 fields must exist and be the
   right types. Bad shape is a 4xx, not a stored event.
3. **Rate limit and replay guard** — 600 events/minute per source, and a
   duplicate `event_id` is refused (`duplicate event_id`) against a 200k-entry
   seen window. This is why every simulated run mints a fresh **run tag**.
4. **Envelope verification** → `valid`, `unsigned`, `tampered`, or an
   **unknown organ**. Anything that is not `valid` is **quarantined before
   detection** and no rule runs on it. This ordering is the security property:
   an unauthenticated sender cannot generate a finding, and a broken sensor
   cannot accuse a host.
5. **Detectors** — the event's `organ` names exactly one of the eight
   `OrganSpec`s in `apps/infra/detectors/registry.py`; each rule declares the
   payload features it needs and a predicate over them.
6. **Campaign fusion** — events sharing a `campaign_id`/`case_id` collapse into
   one campaign with an entity set, a size, a max severity and a risk score.
7. **Proposals** — a deterministic planner proposes containment for fused
   campaigns (21 proposals in the reference replay).
8. **Governor** — `packages/governance/safety.py`, five ordered rules. It has no
   override method, and there is no override route.
9. **Execution** — `DryRunExecutor` only. It records an intention and marks it
   `SIMULATED`. No real containment exists in the codebase, and
   `tools/check_no_live_executor.py` fails the build if one appears.
10. **Ledger** — each sealed finding, decision and execution is appended with a
    monotonically increasing `seq` and a hash chain back to `GENESIS_PREV`.

Console read paths: `/v1/state`, `/api/state` (the gateway's layered view),
`/v1/quarantine`, `/v1/decisions`, `/v1/metrics`, `/v1/ledger/verify`,
`/api/infra/status|capabilities|detectors|scenarios`.

## 4. The eight organs, and what each one actually computes

Rings group the organs by where the attack is visible
(`apps/infra/detectors/registry.py`). These are **deterministic threshold rules
over named numeric features**. The names honour the mathematics they were
informed by — they are not a claim that a physical model is being simulated, and
nothing here is measured against real-world attack traffic.

| Ring | Organ | Rule id | Fires when |
| --- | --- | --- | --- |
| 1 Perimeter identity | `bec_spectral_filter` | `BEC-RANK1-CONDENSATION` | `condensation_ratio ≥ 0.72` **and** `session_count ≥ 4` — many identity sessions collapsing onto one dominant direction |
| 1 | `cookie_fluid_turbulence` | `COOKIE-TURBULENT-REPLAY` | `reynolds_number > 2300` **and** `cookie_replay_count ≥ 2` — replay cadence past the laminar boundary |
| 2 AI-agent defence | `bragg_fft_firewall` | `BRAGG-FFT-PEAK`, `BRAGG-FIEDLER-SPLIT` | `fft_peak_ratio ≥ 0.65` (periodic adversarial-suffix energy) or `fiedler_value ≤ 0.12` (prompt/document token graph fractures) |
| 2 | `hessian_lyapunov_guard` | `HESSIAN-LYAPUNOV-CLIFF` | `lyapunov_exponent > 0.35` **and** `curvature > 1.5` — a diverging trajectory over sharp curvature |
| 3 Endpoint silicon | `page_curve_trap` | `PAGECURVE-PARITY-BREAK`, `PAGECURVE-ENCRYPT-BURST`, `PAGECURVE-ENTROPY-SHADOW` | honey-block XOR parity breaks; or `encrypt_events_per_min ≥ 400`; or `entropy > 7.2` with a shadow-delete flag |
| 3 | `landauer_thermal_audit` | `LANDAUER-POWER-RESIDUAL` | `power_residual_w > 12.0` — package power the instruction rate cannot explain |
| 4 Network healing | `hashimoto_percolation` | `HASHIMOTO-CASCADE-RISK` | `spectral_radius > 1.0` — non-backtracking spectrum says a cascade percolates |
| 4 | `muts_ebpf_repair` | `MUTS-MISMATCH-REPAIR`, `MUTS-REPEAT-BLOCKED` | dual-strand invariant mismatch; or a repeat mismatch on an already-spliced shield |

Three teaching points hide here:

* Every rule declares `required` payload features, and `OrganSpec.evaluate`
  **skips a rule whose features are absent** before testing its predicate —
  "missing features are not evidence". That is the anti-hallucination property,
  and it is why a benign step on the same organ produces nothing.
* An organ reports **the first rule that matches, one finding per event**. So a
  ransomware step carrying both a parity break and 512 encrypt events/min is
  reported as `PAGECURVE-PARITY-BREAK`, not as two findings; the burst rule is
  what fires on its own when parity is intact.
* Each organ ships three fixture bundles — `firing`, `silent`, `missing` — in the
  registry itself. Docs, evals and the console demos all copy those payloads;
  nothing hand-waves a payload into existence.

## 5. Governance: five rules, in order, with no back door

`packages/governance/safety.py`. A proposal is refused by the **first** rule that
matches:

| Rule | Refuses |
| --- | --- |
| `G0-UNPLANNED` | the proposal doesn't carry the canonical planner provenance |
| `G1-CROWN-LOCK` | anything touches a Tier-0 / crown asset (EHR, ICU monitor, the VLANs that hold them) |
| `G2-CROWN-GATEWAY` | anything cuts a crown gateway edge, which is immutable |
| `G3-BLAST-CAP` | blast radius exceeds the cap of 3 assets |
| `G4-NON-DRY-RUN` | the action is not on the dry-run allowlist (3 actions allowed) |

Otherwise `G4-ALLOW-DRY-RUN` allows it — and "allows" means *the dry-run
executor may record an intention*. In the reference governance run: 21
proposals, 12 allowed, 9 refusals, 1 crown-cut attempt rejected, 0 real actions,
admin override impossible. Refusals are the interesting part of a SOC demo: they
show the safety envelope is doing work rather than decoration.

## 6. The ledger: why "append-only" is load-bearing

`packages/ledger/runtime_ledger.py`. Each entry seals a hash over
`seq + prev_hash + payload`, chained from `GENESIS_PREV`. `/v1/ledger/verify`
returns `{ok, valid, height, first_bad_seq, reason: "chain intact"}` — that is
the chain the console and the demos read, and it lives inside the running
process. Separate from it, `python -m packages.ledger.cli verify|tail|replay`
verifies the **file-backed** shared audit ledger (`--ledger PATH`, one JSONL
record per line); on a fresh checkout it reports `{"valid": true, "entries": 0,
"head": "GENESIS"}`, which means "no file-backed records yet", not "the demo's
ledger is empty".

Consequences you should be able to state on stage:

* A demo **cannot be edited after the fact** — including by us. Triggering
  scenarios raises the height; nothing on the console lowers it.
* **Reset never erases evidence.** The Attack Lab's Reset clears the browser's
  view and starts a new run tag; the page says so, because that is the honest
  limit of what a client-side reset can do.
* The console is read-only. Attempting an append through it is a `403`, and a
  write attempted with a read token in the query string is a `401`.

## 7. The Citizen half

Routes live in `apps/citizen/api.py` (26 app routes, 9 feature flags on the
capability card). The invariants are asserted by a gate: **no raw score reaches
the citizen, no verdict is ever "safe", no PII leaves the phone**.

* **MessageGuard** (`packages/messageguard/`, `apps/citizen/messageguard.py`) — a
  deterministic token-and-pattern screen over **text**, in `en`, `hi`, `te` and
  Hinglish, organised into six scam families: `urgency`, `money_action`,
  `authority`, `credential`, `link_grab`, `prize`. It returns a band with
  plain-language reasons and the helpline **1930**, and states that nothing is
  recorded and no synthetic-speaker detection is performed. Measured on 538
  hand-authored fixtures (402 scam / 136 benign): 96.8% accuracy, 99.2%
  detection, 10.3% false-positive rate — **hand-authored / in-distribution only**;
  real-world recall and FPR are UNMEASURED.
* **Risk fusion / VIGIL verdict** — independent signals (transcript verdict,
  message verdict, campaign linkage, repeat contacts, the user's own doubt) are
  combined with a noisy-OR into one bounded band. If evidence is too thin it
  returns `LOW_CONFIDENCE` rather than a reassuring answer, and the advisory
  text is localized (Telugu for `te`).
* **Report rail (Citizen Spine)** — files a signed `raksha-event-v1` report
  carrying **category and severity band only**, never the message body, so the
  citizen leg can fuse with the infra leg. With no network, the PWA queues the
  report offline and marks it `offline` until it is sent.
* **Family mode / panic** — a protected-contact view plus a one-tap 1930 handoff.
* **Retention** — `/api/citizen/retention` publishes the policy the runtime
  actually enforces: bounded in-memory sessions (3 concurrent, 300 s TTL, purged
  after use), no transcript store in-process.
* **VIGIL image privacy** (`packages/vigil/`) — a real TorchScript model
  (`PrivacyNet`, 4,428,047 params, 18,450,009 bytes, 384-px input, 7 semantic
  classes, 4 protection policies) running **CPU-only**. It segments facial
  regions and applies a chosen transform — seeded Gaussian noise,
  structured-frequency perturbation, or composite redaction — then sanitises PNG
  metadata and purges the session. Local, model-artifact metrics only: 88.4%
  independent mIoU, 98.1% face recall. **Privacy efficacy is UNMEASURED**; no
  deepfake-prevention, face-recognition-defeat or anonymity claim is made, and
  the card lists those as claims-not-made.
* There is no Commander/LLM in the loop anywhere: `commander_model: false`, and
  the Citizen gateway reports `model_backed: true` only for the VIGIL weights.

## 8. The console ("Phosphor") and its gateway

`frontend/` is a Next.js app built to a **static export** and committed under
`packages/frontend/static`, which **both** Python apps serve. Same bundle, two
origins. Eight views:

| View | Route | What it teaches |
| --- | --- | --- |
| Call Screen | `/console/call-screen` | paste a transcript, get an advisory verdict |
| VIGIL | `/console/vigil` | the fused band and its reasons |
| Citizen Spine | `/console/citizen-spine` | the signed report rail |
| Message Guard | `/console/message-guard` | the token families behind the screen |
| Rings | `/console/rings` | organ liveness across the four rings |
| Red Team | `/console/red-team` | the three-act sandbox campaign replay |
| Governance | `/console/governance` | decisions, refusals, ledger verification |
| Attack Lab | `/console/attack-lab` | trigger the simulated scenarios |

The important architectural idea is the **same-origin gateway**
(`packages/frontend/gateway.py`): the browser never holds a token and never talks
to a second host. It calls `/api/gateway/...`; the server injects the scoped
token (`RAKSHA_FRONTEND_READ_TOKEN`, falling back to the observer token), maps
the call to the real Citizen or Infra route, and returns structured errors. That
is also why both origins can serve every view, and why a downed backend shows up
as an honest "Service offline" panel instead of a frozen number. The state view
additionally layers `recent_events`, `governor`, `organs_observed` and the
`fortress.*` rollups onto `/api/state` so one poll refreshes the whole board.

`tools/check_frontend_integration.py` proves statically that every path the
console calls resolves to a real route, that no credential or absolute backend
URL reaches the bundle, and that the committed export matches a fresh build.

## 9. The two demos, and why the data is honest

* **Fake-hospital exercise** (`/demo/hospital`, `apps/infra/demo/hospital.py`) —
  a 12-step synthetic attack series against a made-up hospital topology (17
  assets, crown VLANs), run in an **isolated runtime** with its own ledger, and
  start/step/play/reset controls. Good for a "walk a narrative" moment.
* **Attack Lab** (`/console/attack-lab`, script in
  `apps/infra/demo/scenarios.py`) — 8 scenarios, 38 steps, one dedicated
  **Trigger** button each, plus Run all and Reset. The library covers suspicious
  login/replay, a ransomware sweep, a coordinated AI-agent flood, a hostile
  document, an infrastructure anomaly, a kernel/module tamper, a staged
  exfiltration and a **benign control**; every one of the eight organs is used.
  Steps break down as 20 firing, 13 quiet, 5 held.

The Attack Lab's honesty mechanism is worth understanding, because it is the
answer to "is this theatre?":

* The page **only renders** the scripted *inputs* and their *expectations*, read
  live from `GET /api/infra/scenarios`. It never renders a detection number.
* Pressing Trigger posts those inputs through the same signed-ingest path a real
  organ uses; the held (unsigned / forged) steps are sent **as built**, so the
  quarantine you see is the runtime's decision.
* Every tile, timeline row, `seq` and Governor count is polled from
  `/api/gateway/spine/api/state`. Dashboard movement is observed, not animated.
* Each step carries an expectation (`finding` / `no_detection` / `quarantine`),
  and the UI flags `≠ EXPECTED` if the engine disagrees — drift is visible on
  stage rather than hidden. `tools/check_frontend_integration.py` re-derives all
  38 steps against the registry on every CI run, so the script cannot rot.
* Every payload's summary, `campaign_id` (`SIMULATED-<scenario>-<tag>`) and
  `case_id` carry the SIMULATED label, so an exported event can never be mistaken
  for real telemetry after it leaves the page.

## 10. How measurement and claims are governed here

There is exactly **one** measurement path: `evals/run_evals.py` →
`evals/results.json` → generated `EVALS.md`. Three gates police the language:

* `tools/check_eval_drift.py` — `EVALS.md` must match the JSON; nobody edits a
  percentage by hand.
* `tools/check_claims_ledger.py` — every standalone number in outward docs
  (`summary.md`, `README.md`, `docs/STATUS.md`, `CHANGELOG.md`, the release
  notes) needs a conditioned row in `evals/claims_sources.json`. No condition, no
  number.
* `tools/check_code_purge.py` — retired experiment code and its hash pins must
  stay gone, so old claims can't resurrect.

The vocabulary this enforces is the one to use in the talk: *fixture*, *sandbox*,
*hand-authored / in-distribution*, *synthetic*, *UNMEASURED*. Each number in
[EVALS.md](EVALS.md) is labelled with the condition that bounds it — which is why
"96.8% on hand-authored fixtures" and "real-world UNMEASURED" are both true and
both must be said.

## 11. The gate set (what `make ci` actually proves)

`tools/` is the part of this repository that makes the claims defensible:

* `check_phase910_integration.py` — the release contract: exactly two apps, VIGIL
  neural weights allowed and active, Infra deterministic and read-only, the demo
  isolated and dry-run, one eval path, and every canonical file present.
* `check_no_live_executor.py`, `check_no_secrets.py`, `check_code_purge.py`,
  `check_boot_manifest.py`, `check_vigil_assets.py` (hashes and sizes of the
  committed weights), `verify_runtime_ledger.py`.
* `check_frontend_integration.py`, `check_local_links.py`,
  `check_claims_ledger.py`, `check_eval_drift.py`, plus the phase checkers
  `check_phase3_contracts.py`, `check_phase4_citizen.py`,
  `check_phase5_messageguard.py`, `check_phase678_integration.py`.
* HTTP smokes that boot real servers: `run_frontend_smoke.py` (443 checks across
  both origins, including every Attack Lab scenario over real HTTP),
  `run_infra_smoke.py`, `run_hospital_demo_smoke.py`, `run_vigil_smoke.py`.
* Four Node tests for the PWA surfaces, under `raksha-code/tests/`
  (`spine_delivery`, `queue`, `panic_family`, `infra_hospital_demo`), driven by
  `tools/run_phase4_node_tests.py`; `launch_apps.py --check` for the launcher's
  13-check preflight.

A green `make ci` is what the runbook's numbers mean. It currently runs 54
`OK:` lines.

## 12. Five exercises — one per presenter

Do these yourself; they take about ten minutes each and they turn the script into
personal knowledge.

1. **Trace one event.** `.venv/bin/python -c "…" `: import the registry, build
   one `cookie_fluid_turbulence` firing fixture, call `detect(event,
   key=ingest_key())`, and read the `DetectionResult`. Then drop `reynolds_number`
   to 1400 and watch it become "verified; required features absent or benign".
   *You now understand detection better than the slide does.*
2. **Break a signature.** Take any built event, change one payload value, and
   ingest it. It must land in `/v1/quarantine` as `tampered` with **zero**
   detections, and the ledger must not gain a finding. That is
   quarantine-before-detection, proven by hand.
3. **Prove the ledger.** Run a scenario, then
   `curl -s -H 'X-API-Token: demo-observer-token' http://127.0.0.1:8090/v1/ledger/verify`
   and note `height`; press Reset in the UI, re-read, and confirm the height did
   not fall. Then trigger the same scenario twice *without* letting a new tag be
   minted (or replay one by hand with its old `event_id`s) and count the
   `duplicate event_id` refusals shown as `REFUSED`.
4. **Read the evals cold.** Open `EVALS.md` and, for each section, name the
   condition line and the source line. Then delete one conditioned number from
   `evals/claims_sources.json` and run
   `.venv/bin/python tools/check_claims_ledger.py` — watch it fail, then restore
   the file. *You now know why the numbers are safe to say out loud.*
5. **Break the demo on purpose.** Point one console fetch at a dead port
   (change `RAKSHA_INFRA_PORT` for one app, or just `./stop.sh` with the other
   origin's tab open) and confirm the page shows "Service offline" with a Retry
   button rather than stale numbers, and that `GET /api/gateway/status` names
   the unreachable backend. This is the failure path you'll use on stage.

## 13. Misunderstandings worth pre-empting

* *"The detection is AI."* No. Organs are threshold rules over declared
  features, and the Governor is deterministic by design. The only model in the
  build is VIGIL's image-privacy network, in the Citizen app, not in the security
  decision path.
* *"The dashboard numbers are canned for the demo."* The inputs are canned and
  labelled; every output number is read from the running runtime.
* *"It stopped ransomware."* It *detected a simulated encryption signature* and
  *planned* a dry-run containment. `real_action_count: 0`, always.
* *"Reset wipes the evidence."* It clears the view; the ledger is append-only.
* *"We measured it in production."* Nothing here is production-measured;
  real-world accuracy, recall, FPR and privacy efficacy are UNMEASURED.
* *"The hospital demo is live telemetry."* It is a synthetic organisation in an
  isolated runtime with its own ledger; it cannot touch the shared runtime.

## 14. Where to read next

`docs/STATUS.md` (current state, in the project's own words) →
`README.md` (commands and layout) → `EVALS.md` (what is measured, and how) →
`frontend/README.md` (gateway and console) → `apps/infra/README.md` (Attack Lab
section) → `packages/vigil/README.md` (model loading and retention) →
`tools/README.md` (what each gate proves) → the
[presentation demo script](PRESENTATION_DEMO_SCRIPT.md) for the runbook itself.
