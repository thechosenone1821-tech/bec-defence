# Governance package

Phase 3 adds the no-bypass `SharedActionGate`: an event must pass
`packages.contracts.envelope.validate_envelope()` and then receive a Governor
`APPROVED` decision before any optional dry-run executor runs. Unsigned,
tampered and Governor-refused actions never reach the executor.

`governor.py` remains the compatibility facade over the shipped deterministic
PolicyEngine. The full Governor/TCB twins/FIDO2 and enterprise G1–G4 merge
remains Phase 7. No app may bypass this package. See
[`../contracts/guard.py`](../contracts/guard.py) and
[`../../raksha/PHASE3_CONTRACT_SPINE.md`](../../raksha/PHASE3_CONTRACT_SPINE.md)
and [`../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md).
