# Shared packages

Apps integrate through this directory, not through each other. This is the only
shared integration layer in the two-app system.

- [`contracts/`](contracts/) owns Phase 3 canonical JSON, signed envelope,
  verdict/legacy bands, `MSG-*` catalogue, config pins, auth scopes,
  sanitizer/entity rules, backend routes, reserved VoiceGuard slot, no-bypass
  gate, and Phase 4 shared i18n/reason-rendering logic.
- [`spine/`](spine/) exposes the shared spine facade, config pins and backend
  contract. Its legacy `spine.*` compatibility imports are deliberate.
- [`ledger/`](ledger/) owns one `append / verify` adapter and one CLI.
- [`governance/`](governance/) exposes the deterministic PolicyEngine facade and
  the Phase 3 signature + Governor action gate.

Phase 4/5 do not merge the apps. Phase 5 keeps the one `MSG-*` catalogue here;
Citizen sentences live in
[`../apps/citizen/copy.py`](../apps/citizen/copy.py); shared rendering logic
lives in [`contracts/i18n.py`](contracts/i18n.py). Run
[`../tools/check_phase4_citizen.py`](../tools/check_phase4_citizen.py) to verify
the boundary; run `python tools/run_phase4_pytest.py` for the no-AI subset. See
[`../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../raksha/PHASE4_CITIZEN_CONSOLIDATION.md)
and [`../raksha/PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`](../raksha/PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md).

## Phase 6–8 active runtime

`packages/spine/runtime.py` is the one active Infra runtime;
`packages/governance/safety.py` owns one planner/Governor/dry-run executor;
`packages/ledger/runtime_ledger.py` owns the append-only runtime ledger. Older
compatibility facades remain import-safe but no longer import `spine.bus` or an
AI model. See [`../raksha/PHASE678_UNIFIED_INTEGRATION.md`](../raksha/PHASE678_UNIFIED_INTEGRATION.md).
