# Shared packages

These packages are the only shared integration layer between the two apps.

- `contracts/` owns canonical JSON, reason codes, bands, config pins, envelope signing, backend route cards and separation policy.
- `spine/` owns the deterministic Infra runtime and dry-run surfaces.
- `governance/` owns the Governor, planner, dry-run executor and disabled Commander card.
- `ledger/` owns the append-only runtime ledger.
- `vigil/` owns the active TorchScript image-privacy runtime and its weights.

The VIGIL model runtime imports Torch, TorchVision and OpenCV only inside `packages/vigil`. Infra does not import VIGIL. Real-world privacy efficacy remains UNMEASURED. See the [VIGIL runtime notes](vigil/README.md) and [status](../docs/STATUS.md).
