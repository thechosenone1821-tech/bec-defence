#!/usr/bin/env python3
"""End-to-end smoke test for VIGIL mounted inside the Citizen FastAPI app."""
from __future__ import annotations

import io
import zipfile

import cv2
import numpy as np
from fastapi.testclient import TestClient

from apps.citizen.api import build_app
from packages.vigil.config import DEFAULT_WEIGHTS_CANDIDATES


def _synthetic_face_png() -> bytes:
    image = np.full((360, 480, 3), 70, dtype=np.uint8)
    cv2.ellipse(image, (240, 180), (90, 120), 0, 0, 360, (200, 170, 150), -1)
    cv2.ellipse(image, (210, 160), (16, 8), 0, 0, 360, (40, 30, 30), -1)
    cv2.ellipse(image, (270, 160), (16, 8), 0, 0, 360, (40, 30, 30), -1)
    cv2.ellipse(image, (240, 230), (40, 14), 0, 0, 360, (90, 50, 50), -1)
    ok, buffer = cv2.imencode(".png", image)
    assert ok, "synthetic PNG encoding failed"
    return buffer.tobytes()


def main() -> int:
    client = TestClient(build_app(bus_url=""))

    dashboard = client.get("/vigil/", follow_redirects=False)
    assert dashboard.status_code == 200, dashboard.text
    assert client.get("/vigil/static/app.js").status_code == 200
    overview = client.get("/vigil/api/overview")
    assert overview.status_code == 200, overview.text
    model_status = overview.json()["model_status"]
    assert model_status["is_neural_active"] is True, model_status
    assert model_status["weights_file"] == DEFAULT_WEIGHTS_CANDIDATES[0].name, model_status

    upload = client.post(
        "/vigil/api/sessions/upload",
        files={"file": ("synthetic_face.png", _synthetic_face_png(), "image/png")},
        data={"auto_resize": "true"},
    )
    assert upload.status_code == 200, upload.text
    session = upload.json()
    sid = session["session_id"]
    print(f"upload: session={sid} dimensions={session['working_dimensions']} regions={len(session['regions'])}")
    print(f"upload: model_mode={session['perception_metadata']['model_status']['system_mode']}")

    execution = client.post(
        "/vigil/api/vigil/execute",
        json={
            "session_id": sid,
            "config": {
                "policy_id": "policy_strict",
                "method": "gaussian_noise",
                "noise_sigma": 25.0,
                "random_seed": 42,
                "apply_noise_to": "selected_regions",
                "mask_dilation_px": 0,
            },
            "run_evaluation": True,
        },
    )
    assert execution.status_code == 200, execution.text
    report = execution.json()
    audit = report["audit_report"]
    evaluation = report["evaluation_report"]
    assert report["transformed_png_url"].startswith("data:image/png;base64,")
    assert "controlled_transforms" in evaluation and "detector_retention" in evaluation
    print(f"execute: processing_time_ms={report['processing_time_ms']} audit={audit['overall_audit_status']}")
    print(f"execute: modified_target_ratio={audit['modified_pixels_within_target_ratio']:.4f} mode={audit['system_mode']}")

    png = client.get(f"/vigil/api/export/{sid}/image.png")
    audit_json = client.get(f"/vigil/api/export/{sid}/audit.json")
    bundle = client.get(f"/vigil/api/export/{sid}/bundle.zip")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    assert audit_json.status_code == 200 and bundle.status_code == 200
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        names = archive.namelist()
    assert any(name.endswith(".png") for name in names)
    assert any(name.endswith(".json") for name in names)
    print(f"export: png={len(png.content)}B json={len(audit_json.content)}B zip={len(bundle.content)}B names={names}")

    verify = client.post(
        "/vigil/api/security/verify-png",
        files={"file": ("vigil.png", png.content, "image/png")},
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["is_clean_png"] is True
    assert verify.json()["all_crc32_valid"] is True

    deleted = client.delete(f"/vigil/api/sessions/{sid}")
    assert deleted.status_code == 200 and deleted.json()["purged"] is True
    after = client.get("/vigil/api/overview").json()
    print(f"purge: recent_sessions={len(after['sessions']['recent_sessions'])} rss_mb={after['hardware_profile']['process_rss_mb']}")
    print("OK: VIGIL Citizen HTTP smoke passed; neural weights active, exports sanitized, session purged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
