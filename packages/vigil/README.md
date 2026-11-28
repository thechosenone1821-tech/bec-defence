# VIGIL runtime

VIGIL is a model-backed image-privacy package mounted by the Citizen FastAPI app under `/vigil/`. It is not a third service. The mount also records VIGIL integration on the Citizen app state. The active deployment artifact is the committed TorchScript PrivacyNet checkpoint named in [model_manifest.json](model_manifest.json).

## Routes

- `/vigil/` serves the dashboard and `/vigil/static/` serves same-origin assets.
- `/vigil/api/overview` reports model status, hardware limits, policies and session summaries.
- The Citizen backend exposes `/api/citizen/vigil/status` for a same-origin model status view.
- `/vigil/api/sessions/upload` validates an image and returns detected regions.
- `/vigil/api/vigil/execute` applies a configured transform, optionally evaluates it and returns an audit report.
- `/vigil/api/export/...` serves sanitised PNGs, audit JSON and ZIP bundles.
- `DELETE /vigil/api/sessions/{id}` purges pixel buffers from process memory.

## Transformations

The privacy engine supports solid fill, pixelation, blur, seeded Gaussian noise, structured-frequency perturbation and composite redaction with hard pixelation for QR/text/licence-plate regions plus seeded noise elsewhere. Seeds make transforms reproducible. Exported PNGs are stripped of metadata and CRC-verified.

## Honesty and retention

Local metrics in the manifest and training history describe committed artifacts. Real-world privacy efficacy remains UNMEASURED. VIGIL does not claim deepfake prevention, modern face-recognition defeat or an anonymity guarantee. Sessions live in process memory only, expire by TTL, are capped, and are purged on explicit delete, expiry or restart. See [retention.py](../../apps/citizen/retention.py), [status](../../docs/STATUS.md) and [generated evaluation report](../../EVALS.md).
