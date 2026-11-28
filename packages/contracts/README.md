# Shared contracts

This package owns canonical JSON, reason codes, verdict bands, auth scopes, pinned Infra configuration, envelope signing, backend route cards, the shared action gate and the app-separation policy. It contains no app code, no model runtime and no live executor. Citizen and Infra consume these contracts through the shared package layer. The active VIGIL runtime is declared by `separation.py` but implemented under `packages/vigil`.
