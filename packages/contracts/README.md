# Shared contracts — Phase 3 source of truth + Phase 4 i18n

This package is the single owner of the contracts that both apps must speak.
It contains no app code and imports no VoiceGuard/MAYA implementation.

| Module | One canonical thing |
| --- | --- |
| `canonical.py` | byte-exact canonical JSON and hash rule |
| `envelope.py` | signed-event validation across `mac`, `signature` and `sig` wire profiles |
| `bands.py` | verdict bands, edges and legacy organ band map |
| `reasons.py` | `MSG-*` reason catalogue |
| `entities.py` | sanitizer regexes, opaque-token prefixes and entity-graph path |
| `config.py` | pinned config paths, hashes, auth scopes and key env names |
| `backend.py` | canonical spine-v2 / enterprise-i1 route contract |
| `i18n.py` | Phase 4 language/copy rendering logic; imports no app or model code |
| `voiceguard.py` | reserved future VoiceGuard slot with no logic import |
| `guard.py` | signature + Governor `SharedActionGate` |
| `separation.py` | allowed/forbidden imports, no-bypass roots and no-AI-model roots |

[`config_pins.json`](config_pins.json) is generated and checked by:

```bash
python -m packages.contracts --write-pins   # audited re-baseline only
python -m packages.contracts                # check 5 pins
python ../tools/check_phase3_contracts.py   # Phase 3 checker
python ../tools/check_phase4_citizen.py     # Phase 4 Citizen checker
python ../tools/run_phase4_pytest.py        # deterministic no-AI pytest subset
```

See [`../../raksha/PHASE3_CONTRACT_SPINE.md`](../../raksha/PHASE3_CONTRACT_SPINE.md),
[`../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md)
and [`../../raksha/adr/ADR-011-unified-contracts.md`](../../raksha/adr/ADR-011-unified-contracts.md)
and [`../../raksha/adr/ADR-012-citizen-consolidation.md`](../../raksha/adr/ADR-012-citizen-consolidation.md).
