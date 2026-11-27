# RAKSHA — combined Citizen and Infra system

One repository, exactly two apps, one shared spine. The system is deterministic
and runs no AI model, Commander, SLM, Ollama endpoint, frozen VoiceGuard/MAYA
inference, live executor or real containment action. Dry-run is the only
executor mode.

## Start here

```bash
make install   # one install command
make test      # one test command: Python suites, browser suites, deterministic checkers
make eval      # one eval drift command: corpus, replay, results, EVALS.md, claims ledger
make eval-generate  # regenerate the one EVALS.md and claims ledger
make run       # one process launcher: Citizen app + Infra/SOC console
make ci        # install + test + eval + all deterministic CI gates
```

For the full AI handoff, reading order and future-integration playbook, read
[`summary.md`](summary.md). The launcher binds both services on all interfaces
for the Arena preview. The
Infra console is the root redirect; the Citizen app serves its own PWA. Read
[`docs/STATUS.md`](docs/STATUS.md) for the single frozen status board and
[`docs/README.md`](docs/README.md) for the document map.

## Architecture

- [`apps/citizen/`](apps/citizen/) — the Citizen PWA, MessageGuard scorer,
  report rail and honest feature flags. VoiceGuard remains a frozen seam.
- [`apps/infra/`](apps/infra/) — the signed telemetry API, one detector registry,
  read-only SOC console and unified backend.
- [`packages/contracts/`](packages/contracts/) — one reason catalogue, bands,
  signed envelope, routes, pins and separation rules.
- [`packages/spine/`](packages/spine/) — the one runtime, bus facade and console
  surfaces.
- [`packages/governance/`](packages/governance/) — one planner, Governor and
  dry-run executor; crown cuts and admin overrides are impossible.
- [`packages/ledger/`](packages/ledger/) — one append-only hash-chain path.
- [`evals/`](evals/) — one deterministic corpus generator, replay player,
  measurement runner, generated [`EVALS.md`](EVALS.md) and claims ledger.

## Measurement honesty

Every measured number in [`EVALS.md`](EVALS.md) carries a condition — fixture,
synthetic, sandbox, hand-authored or real-world UNMEASURED — and a source row in
[`evals/claims_ledger.json`](evals/claims_ledger.json). No number belongs in a
README, status page, changelog or pitch without that row. Real-world accuracy,
latency, uptime, recall and false-positive rate are UNMEASURED. Sandbox fixtures
are never evidence of field performance.

## Scope and re-entry

The ten-phase combined-system board is frozen. VoiceGuard / MAYA is not part of
this release and is not evidence of completion. A separate future Phase Eleven
may open only when the voice build is ready and the written re-entry gate in
[`docs/STATUS.md`](docs/STATUS.md) is satisfied. Until then, frozen assets stay
unchanged and VoiceGuard evals stay out of the unified runner.

Historical uploads, retired standalone projects and build logs live under
[`archive/provenance/`](archive/provenance/) with integration notes. They are
provenance, not active runtime paths. For release history see
[`CHANGELOG.md`](CHANGELOG.md) and the phase report
[`raksha/PHASE910_UNIFIED_RELEASE.md`](raksha/PHASE910_UNIFIED_RELEASE.md).
