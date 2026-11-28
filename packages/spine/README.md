# Shared spine

Phase 3 makes this the shared spine facade over the shipped `raksha-code/spine`
runtime. It exposes one backend contract, one config-pin set, shared canonical
JSON helpers, sanitizer/entity-graph facades, telemetry MAC compatibility and
one ledger CLI entrypoint.

Apps import `packages.spine`, never each other and never private `spine.bus`,
`spine.governor`, `spine.ledger` or `spine.containment` bypass roots. The full
bus/API/WS implementation merge remains Phase 8. See
[`../contracts/`](../contracts/) and
[`../../raksha/PHASE3_CONTRACT_SPINE.md`](../../raksha/PHASE3_CONTRACT_SPINE.md)
and [`../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md`](../../raksha/PHASE4_CITIZEN_CONSOLIDATION.md).
