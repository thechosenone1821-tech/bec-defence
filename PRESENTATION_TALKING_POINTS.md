# Presentation — who says what

A five-person run of the RAKSHA demo: 22 minutes on stage, 5-minute buffer, one
speaker per concept so nobody has to context-switch while clicking. Names are
written as Speaker 1–5; swap in the real names before rehearsing.

Ground rule for all five: **every attack shown on stage is simulated.** Say
"simulated", "scripted", "sandbox" out loud. Never say we stopped, blocked or
caught a real attack, never quote a real-world accuracy or SLA, and never claim
the system took an action on a host. If a judge or customer pushes, use the
three escape lines at the bottom — they are all literally true and they are the
claims the repository's own gates protect.

## Role map

| Who | Segment | Min | Owns this idea | Drives the screen |
| --- | --- | ---: | --- | --- |
| Speaker 1 — Framing | Why this exists | 3 | Two sides of one scam: the phone call and the network behind it | none (title only) |
| Speaker 2 — Citizen | The person-facing half | 5 | Advisory help that never overclaims | `:8095` Call Screen, VIGIL |
| Speaker 3 — Detection | The infra half and its organs | 5 | Eight independent mathematical organs, quarantine before accusation | `:8090` Rings |
| Speaker 4 — Attack Lab | The live demo | 5 | Trigger a simulated attack, watch real detection and real response | `:8090` Attack Lab |
| Speaker 5 — Governance & proof | Why to believe it | 4 | Deterministic Governor, dry-run only, append-only ledger, 54 gates | `:8090` Governance |

Total 22 min. Every handoff is one sentence long and is written out below, so
the next speaker can start talking while the page loads.

## Running order

### Speaker 1 — Framing (0:00–3:00)

Say:

- The pitch in one line: *"RAKSHA is one defence spine with two faces — a
  citizen who gets a plain-language warning, and an infrastructure operator who
  gets signed, governed telemetry. Same event contract, same ledger."*
- The problem is a pipeline, not a payload: a scam call ends with someone
  approving a transfer, and that approval walks through real hosts, real
  sessions, real credentials. So both ends are instrumented.
- What the audience will see, in order: a transcript screen, a set of detection
  organs, four scripted attacks triggered live, and the governance layer that
  keeps the whole thing honest.
- One honesty beat up front, before anyone can suspect it later: *"Nothing on
  stage tonight is a real attack. The attack inputs are scripted and labelled
  SIMULATED. Everything downstream of those inputs — detection, quarantine,
  fusion, decisions, ledger entries — is the real engine's own answer."*

Do not say: "real-time threat detection for your enterprise", "AI catches
ransomware", "we blocked X".

Handoff: *"Start with the person on the phone — Speaker 2."*

### Speaker 2 — Citizen (3:00–8:00)

Screen: `http://127.0.0.1:8095/console/call-screen`.

Do, in this order, while saying:

1. Paste the UPI/OTP demand transcript → verdict **CRITICAL**. *"This is a
   deterministic rule screen over words, not a model guessing. It names the
   engine and it says nothing was recorded — no microphone, no audio upload."*
2. Paste a normal message ("the water tanker comes at eight") → a low verdict.
   *"A quiet message stays quiet. That matters more than the alert."*
3. Open **VIGIL** and point at the fused band: transcript verdict, message
   verdict, campaign linkage, repeat contacts, the user's own doubt — fused with
   noisy-OR into one band with plain-language reasons. *"It has an honest band:
   when the signals don't add up it says LOW_CONFIDENCE instead of reassuring
   you. It never outputs 'safe'."*
4. Point at the report rail: **Citizen Spine** files a signed report carrying
   category and severity band only — never the message text. *"That is the
   bridge into the infrastructure half, and it is why no phone data is needed to
   light up the operator view."*

Numbers if asked (from [EVALS.md](EVALS.md), all conditioned on
hand-authored fixtures): 538 fixtures, 96.8% accuracy, 99.2% detection, 10.3%
false-positive rate, four languages including Hinglish. Say the condition
before the number, every time.

Also mention without dwelling: offline queue (screening works with no network,
reports queue), one-tap 1930 helpline, family mode, retention limits.

Handoff: *"Now the other end of the same pipe — Speaker 3."*

### Speaker 3 — Detection organs (8:00–13:00)

Screen: `http://127.0.0.1:8090/console/rings`.

Say:

- *"The organisation side is split into four rings — perimeter identity, AI
  agent defence, endpoint silicon, network healing — and each ring carries two
  organs. Eight organs, one registry, one event contract."*
- Pick two and explain the actual arithmetic so it is clear this is not a
  keyword list: **cookie_fluid_turbulence** fires when a session-cookie replay
  cadence crosses the laminar→turbulent boundary (Reynolds number above 2300
  with at least two replays); **page_curve_trap** fires when a 4 KB honey block's
  XOR parity invariant breaks on first write, or when encryption events per
  minute reaches 400 or more (that one needs no parity break — it is its own
  rule). Full table in
  [PROJECT_CONCEPTS_GUIDE.md](PROJECT_CONCEPTS_GUIDE.md).
- The rule that makes this trustworthy: *"Quarantine happens before detection.
  An event with a missing or forged signature is held and never becomes
  evidence — so a broken sensor cannot accuse a host, and an attacker cannot
  sign their way into the ledger."*
- Fleet column: organs report `OBSERVED` or `QUIET` based on events actually
  seen. *"No heartbeat pretending to be health."*
- Note the dry-run card and the disabled Commander card while it is on screen:
  *"There is no AI model in the decision path here. It is a rule Governor, and
  that is deliberate — a demo answer must be reproducible."*

Handoff: *"Speaker 4 will now trigger attacks. On purpose. All simulated."*

### Speaker 4 — Attack Lab (13:00–18:00)

Screen: `http://127.0.0.1:8090/console/attack-lab`. Click, don't narrate clicks —
Speaker 5 talks over the polling gaps.

Trigger these four, in this order, and point at the named thing each one proves
(verified counts; see [PRESENTATION_DEMO_SCRIPT.md](PRESENTATION_DEMO_SCRIPT.md)):

1. **`suspicious-login`** → 2 detected on the replay rule, **2 held
   unverified** (the unsigned retry and the forged signature), 1 quiet baseline.
   Line: *"Same attack shape, opposite outcomes — and the difference is the
   signature, not our opinion."*
2. **`ai-agent-flood`** → 5 detected across three organs, fusing into one
   campaign. Line: *"Twelve identity sessions, each ordinary on its own; the
   finding is that they collapse onto one dominant direction — and the flood's
   network side plus its consumer-side report fuse into a single campaign."*
3. **`ransomware-sweep`** → 3 detected (`PAGECURVE-PARITY-BREAK` ×2 on the
   encrypt burst and the shadow-delete, plus the victim's consumer-leg report),
   and 2 verified no-finding: the nightly **backup-job** step (busy, but the
   honey-page invariant is intact) and an **endpoint-note** step that carries no
   readable page-curve feature. Line: *"Same organ, different answer — the
   invariant is the signal, and an event with no features gets no accusation."*
4. **`benign-baseline`** (the control) → 6 accepted, 0 findings, 0 quarantines,
   0 decisions. Line: *"Nothing happens here. That's the correct answer, and we
   ship it as a scenario so nobody can accuse the others of being rigged."*

While each run is in flight, call out what is real: timestamps, severity,
per-step status (`DETECTED` / `HELD UNVERIFIED` / `NO FINDING` / `REFUSED`), the
`≠ EXPECTED` drift flag, the SIMULATED alert strip per organ, and the ledger
`seq` numbers climbing.

Then press **Reset** and re-trigger one scenario to show repeatability: *"Every
run gets a fresh run tag, so a re-run cannot double-count. Re-sending the old
tag is refused as a duplicate event id and shown as REFUSED."* Say plainly that
the ledger is append-only, so reset clears the view, not the sealed evidence.

If a card shows `BACKEND ERROR` or the header pill reads `ARMED` and nothing
moves, keep talking for 10 seconds and use fallback step 2 in
[PRESENTATION_DEMO_SCRIPT.md](PRESENTATION_DEMO_SCRIPT.md) — do not restart on
stage.

Handoff: *"The attacks were scripted. What you just saw react was not — Speaker
5."*

### Speaker 5 — Governance, proof and the close (18:00–22:00)

Screen: `http://127.0.0.1:8090/console/governance`, then the status card.

Say:

- The Governor's five ordered rules, and the fact that it has no override
  method: provenance → crown lock → crown gateway → blast cap of three →
  dry-run allowlist. *"The two refusals in a normal run are features: cutting a
  Tier-0 crown asset or widening blast radius is refused even by our own
  planner."*
- `containment.executor_result` reads `dry_run_only`, `real_action_count: 0`,
  and `live_action_paths: 0`. *"There is no code path in this build that touches
  a real host. That is the design constraint, not a demo mode."*
- Ledger: hash-chained, `verify: chain intact`, every finding and decision
  sealed with a `seq`. *"Append-only means the demo can't be edited after the
  fact, including by us."*
- Proof discipline: `make ci` runs 54 gates — HTTP smokes over both apps, the
  frontend integration checker that re-derives all 38 scripted steps against the
  live detector registry, the claims ledger that refuses any unsourced number
  in our docs, retired-code purge, secret scan, link check. *"If a demo number
  and the engine disagree, CI fails, so the page cannot quietly lie."*
- Close on the boundary, unprompted: *"What we claim: deterministic detection
  and governance over signed telemetry, and advisory screening on the citizen
  side, measured on hand-authored fixtures. What we do not claim: real-world
  accuracy, recall, false-positive rate, privacy efficacy — all UNMEASURED — and
  we claim no real-world action ever taken."*

## If you get asked

| Question | Answer to | The honest answer |
| --- | --- | --- |
| "What's the accuracy on real traffic?" | Speaker 5 | "Unmeasured. Our 96.8% is over 538 hand-authored fixtures in four languages; we publish the condition and we don't extrapolate from it." |
| "Is the attack real?" | Speaker 4 | "No — inputs are scripted and labelled SIMULATED. The reactions are the production pipeline's own, which is why the numbers move." |
| "Does it auto-remediate?" | Speaker 5 | "It plans and decides, and executes in dry-run only. Organ control and admin override are refused by rule, not by configuration." |
| "Why a math-y organ instead of ML?" | Speaker 3 | "Because a SOC has to explain a finding. Each rule is a stated threshold over named features, so the answer is reproducible and inspectable." |
| "Where's the model?" | Speaker 2 | "VIGIL's image-privacy runtime is real TorchScript weights, CPU-only, mounted in the Citizen app; its privacy efficacy is unmeasured and it is not in the security decision path." |
| "How do I run this myself?" | Speaker 1 | "`./start.sh`, open the printed URL, four clicks. One file tells you everything: `PRESENTATION_DEMO_SCRIPT.md`." |

## Three escape lines (anyone, any time)

1. *"That number is conditioned on synthetic fixtures — here is what it does and
   doesn't tell you."*
2. *"The inputs are simulated; the engine's answer is real."*
3. *"We don't claim that, and the build refuses to do it either."*

## Rehearsal and pre-flight

- Day before: `make ci` green, then `./start.sh` and walk all four Attack Lab
  scenarios end to end.
- 30 min before: `./start.sh --status` (both running), then
  `curl -s http://127.0.0.1:8090/api/gateway/status | head -c 200` →
  `"citizen":{"ok":true}` and `"spine":{"ok":true}`.
- 10 min before: click **Reset** in the Attack Lab, trigger
  `suspicious-login`, confirm one row is `HELD UNVERIFIED`, then leave it. Do
  not chase a clean board; a fresh stack is `./stop.sh && ./start.sh`.
- Screen: two tabs only — `:8095/console/call-screen` and
  `:8090/console/attack-lab`. Zoom to 125%. Kill notifications.
- Pair practice: Speaker 4 clicks, Speaker 5 narrates over every polling gap.
  Nobody is idle: while a page loads, the other speaker has a line.
- If the laptop has no network at all: everything above is localhost — no
  model download, no database, no broker, no SaaS dependency.
