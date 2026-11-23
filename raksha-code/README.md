# raksha-code — RAKSHA application monorepo

> **Status: M1–M5 shipped.** spine + Sentinel shields + Citizen PWA + RAAVAN
> kill chain + containment planner are present in this branch. The existing
> measured baseline is 67 tests; run \`pytest -q\` for the current checkout.
> **Nothing here performs real-world actions** — the organ-backed executor is
> dry-run by construction (no host ever touched).

## Layout

\`\`\`text
spine/          shared kernel — ported from eigenshield-v2, then hardened for RAKSHA
spine/containment.py  M5: exhaustive min-disruption cut planner (J = C+λD+μR+νA)
evals/run_evals.py    M6: measured baseline × metric table (fixtures only)
  sanitizer.py      zero-trust input normalization (HMAC tokens, injection scrub)
  entity_graph.py   10-min attack graph + campaign correlator v0 (union-find)
  ledger.py         append-only SHA-256 hash-chained evidence ledger
  ledger_anchor.py  HMAC-sealed (seq, head) side anchor
  governor.py       deterministic Governor (schema lock, crown jewel, budgets, FIDO2)
  tcb_core.py / tcb_mirror.py   N-version stateless decision twins (fail closed)
  telemetry_mac.py  organ-signed telemetry (HMAC-SHA256) + replay cache
  tripwire.py       anti-probing AI freeze (human step-up to reset)
  boot_manifest.py  SHA-256 config pinning (--pin/--check)
  canaries.py       ESH_CANARY context tripwires
  sandbox_runner.py whitelist subprocess isolation
  bus.py            FastAPI + WS broker (verified-only ingest)
  orchestrator.py   local SLM planner (Ollama; deterministic fallback offline)
  ledger_cli.py     verify / tail / replay the evidence ledger
  config/           policy.yaml · company_topology.json · manifest.json (pinned)
tests/          pytest — spine, shield, Citizen and VoiceGuard tests
requirements.txt
requirements-voiceguard-onnx.txt  optional ONNX Runtime only; no model weights
\`\`\`

\`citizen/\` — RAKSHA Citizen (M3) — offline PWA + same-origin FastAPI

- \`messageguard/\`: deterministic scam-script scorer (en/hi/te signal families)
- \`voiceguard/\`: two-second audio validation, spectral/LFCC/LPCC features,
  advisory fallback, optional local ONNX adapter (no weights bundled)
- \`api.py\`: health, message/voice screening, and signed Citizen reports;
  voice endpoint requires explicit consent and enforces 16 kHz / 2 seconds
- \`app/\`: PWA home, message screening, consent-first microphone sample,
  incident report, and 1930 helpline link

**VoiceGuard limitation:** the PWA analyses a short microphone sample the
user deliberately records. It cannot intercept cellular or app-call audio.
The fallback does not detect modern neural voice clones; ordinary speech is
INCONCLUSIVE without a separately supplied and validated model.

## Quickstart

\`\`\`bash
cd raksha-code
python -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m spine.boot_manifest --check spine/config/manifest.json
python -m spine.ledger_cli verify
python -m spine.bus --policy spine/config/policy.yaml --topology spine/config/company_topology.json --port 8090
python -m citizen.api --port 8095
\`\`\`

Optional local ONNX Runtime adapter:

\`\`\`bash
pip install -r requirements-voiceguard-onnx.txt
# Supply your separately obtained/trained compatible ONNX model:
export RAKSHA_VOICEGUARD_ONNX=/absolute/path/to/voiceguard.onnx
\`\`\`

The model export contract is one float32 input shaped \`[1, 32000]\` (mono
16 kHz waveform) and one spoof probability or two logits ordered
\`[bonafide, spoof]\`. Model weights are not included. The adapter's mock tests
verify the interface, not model performance.

The VoiceGuard PWA microphone feature requires a secure context (HTTPS or
localhost), a user gesture, and browser microphone permission. The sample is
sent to the configured RAKSHA service only after the consent checkbox is
selected. Use a trusted/self-hosted service.

## Porting notes (honesty log)

- Ported, not imported — \`eigenshield-v2/\` stays untouched; this tree evolves
  independently.
- Executor is DRY-RUN: every tool returns a \`DRY_RUN_*\` status. No host is
  modified.
- Campaign correlator v0 = union-find over shared entity tokens in the sliding
  window. Temporal kernels / weighted fingerprints remain future work.
- \`spine/config/manifest.json\` pins the config set with package-relative
  paths; re-pin with \`--pin\` after any legitimate config change.
