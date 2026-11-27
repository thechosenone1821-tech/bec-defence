# RAKSHA Citizen app boundary

This is the editable Citizen app root and the single Citizen service. It owns:

- `api.py` / `__main__.py`: FastAPI service and PWA host.
- `messageguard/`: Phase 5 single-source deterministic scorer, en/hi/te/Hinglish
  detector interface, legacy organ adapter and sanitized operator CLI.
- `risk/`: bounded risk fusion and citizen-facing explanations.
- `copy.py`: all citizen-facing en/hi/te sentences; rendering logic lives in
  [`../../packages/contracts/i18n.py`](../../packages/contracts/i18n.py).
- `features.py`: hard-disabled VoiceGuard/MAYA and Commander flags;
  `NO_AI_MODELS=True`.
- `voiceguard_interface.py`: documented `DisabledVoiceGuard` seam.
- `retention.py`: model-free consent/retention gate.
- `phase4_shell.py`: runtime-only honest voice-tab overlay for the frozen shell.
- `legacy_voiceguard.py`: the single read-only adapter to the frozen seam, for
  future Phase 11 only; not used by the active Phase 5 path.
- `app/` and `fixtures/`: symlinks to the untouched legacy PWA/fixture trees.

VoiceGuard/MAYA files are **not** part of Phase 2, Phase 3, Phase 4 or Phase 5. They
remain under `../../raksha-code/citizen/voiceguard/` and the existing PWA
directory, and their hashes are pinned by
[`../../tools/frozen_assets.sha256`](../../tools/frozen_assets.sha256). The
voice tab says **"not integrated yet"**, no audio is recorded or scored, and no
clone-detection claim is made.

Run: `python -m apps.citizen --port 8095` (or `python -m citizen.api` for
legacy compatibility). Validate with `python tools/check_phase4_citizen.py`,
`python tools/check_phase5_messageguard.py`, `python tools/run_phase4_pytest.py`
and `python tools/run_phase4_node_tests.py`. See
[`../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md)
and
[`../../raksha/PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](../../raksha/PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md).
