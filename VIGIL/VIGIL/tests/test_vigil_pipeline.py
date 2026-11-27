# tests/test_vigil_pipeline.py
"""
Unit & Integration Tests for VIGIL 2.0
Verifies bug fixes, model constraints, mask exclusion logic, reproducible transformations,
honest auditing, PNG chunk sanitisation, and FastAPI endpoints.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from vigil_app.engines.audit_engine import AUDIT_ENGINE
from vigil_app.engines.evaluation_engine import EVALUATION_ENGINE
from vigil_app.engines.privacy_engine import PRIVACY_ENGINE
from vigil_app.engines.security_engine import SECURITY_ENGINE
from vigil_app.main import app
from vigil_app.models.privacy_net import LazyModelManager, VigilPrivacyNet
from vigil_app.schemas import (
    BoundingBox,
    DetectedRegion,
    TransformationConfig,
)


def _create_synthetic_rgb(width: int = 320, height: int = 240) -> np.ndarray:
    """Creates a deterministic synthetic RGB test image with textured regions."""
    rng = np.random.default_rng(12345)
    img = rng.integers(40, 210, size=(height, width, 3), dtype=np.uint8)
    for x in range(30, 180, 12):
        cv2.rectangle(img, (x, 180), (x + 6, 205), (250, 250, 250), -1)
    return img


def test_model_parameter_count_and_hashlib_fix(tmp_path: Path) -> None:
    """
    Verifies:
    1. VigilPrivacyNet has < 100 Million parameters (~6.4M on torchvision >=0.17; well under the cap).
    2. LazyModelManager._compute_sha256 works (fixing the missing hashlib bug).
    3. Empty 0-byte weights file triggers explicit FALLBACK_HEURISTIC_MODE.
    """
    net = VigilPrivacyNet(num_classes=7, pretrained_backbone=False)
    total_params = sum(p.numel() for p in net.parameters())
    assert total_params < 100_000_000
    # Note: the spec's text claimed 4,230,279 params, but that figure was off for
    # torchvision >=0.17's MobileNetV3-Large encoder. The measured count is 6,394,127,
    # which is still ~15x smaller than the 100M parameter ceiling.
    assert total_params == 6_394_127

    empty_pt = tmp_path / "replace_this_file.pt"
    empty_pt.write_bytes(b"")

    mgr = LazyModelManager(candidate_paths=[empty_pt])
    status = mgr.get_status()
    assert status["system_mode"] == "FALLBACK_HEURISTIC_MODE"
    assert status["is_neural_active"] is False
    # Empty file SHA-256 digest
    assert status["weights_sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_privacy_mask_exclusion_logic_fix() -> None:
    """
    Regression test for Bug #3: when two face regions exist and face #2 is deselected
    (active=False or in excluded_region_ids), the global semantic segmentation mask
    must NOT redact face #2.
    """
    h, w = 200, 300
    seg_mask = np.zeros((h, w), dtype=np.uint8)
    seg_mask[20:100, 20:100] = 1
    seg_mask[20:100, 180:260] = 1

    regions = [
        DetectedRegion(
            region_id="reg_001",
            category="face",
            bbox=BoundingBox(x1=20, y1=20, x2=100, y2=100),
            confidence=0.92,
            detector_source="OpenCV_Haar_FrontalFace",
            active=True,
        ),
        DetectedRegion(
            region_id="reg_002",
            category="face",
            bbox=BoundingBox(x1=180, y1=20, x2=260, y2=100),
            confidence=0.88,
            detector_source="OpenCV_Haar_FrontalFace",
            active=False,
        ),
    ]

    config = TransformationConfig(
        policy_id="policy_strict",
        method="solid",
        excluded_region_ids=["reg_002"],
        mask_dilation_px=0,
    )

    mask, resolved = PRIVACY_ENGINE.build_protection_mask((h, w), regions, seg_mask, config)

    # Active face #1 must be masked (1)
    assert np.all(mask[30:90, 30:90] == 1)
    # Excluded face #2 must be completely unmasked (0)
    assert np.all(mask[20:100, 180:260] == 0)


def test_seeded_gaussian_noise_reproducibility_and_isolation() -> None:
    """
    Verifies that seeded Gaussian noise:
    1. Modifies only pixels inside the protection mask when apply_noise_to='selected_regions'.
    2. Is 100% bit-for-bit reproducible given the same random_seed.
    """
    rgb = _create_synthetic_rgb(200, 200)
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[50:150, 50:150] = 1

    cfg = TransformationConfig(
        method="gaussian_noise",
        noise_sigma=25.0,
        random_seed=999,
        apply_noise_to="selected_regions",
        mask_dilation_px=0,
    )

    out_1, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, [], cfg)
    out_2, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, [], cfg)

    # Identical outputs for identical seed
    assert np.array_equal(out_1, out_2)
    # Background outside mask must remain untouched
    assert np.array_equal(out_1[:40, :40], rgb[:40, :40])
    # Target region inside mask must be modified
    assert not np.array_equal(out_1[50:150, 50:150], rgb[50:150, 50:150])


def test_evaluation_keys_and_honest_audit() -> None:
    """
    Verifies:
    1. Controlled transform keys use safe snake_case (no dots in keys).
    2. AuditEngine does not report PASS when method='none'.
    """
    rgb = _create_synthetic_rgb(240, 240)
    mask = np.zeros((240, 240), dtype=np.uint8)
    mask[40:120, 40:120] = 1

    regions = [
        DetectedRegion(
            region_id="reg_001",
            category="face",
            bbox=BoundingBox(x1=40, y1=40, x2=120, y2=120),
            confidence=0.9,
            detector_source="OpenCV_Haar_FrontalFace",
            active=True,
        )
    ]

    cfg_none = TransformationConfig(method="none", mask_dilation_px=0)
    out_none, meta_none = PRIVACY_ENGINE.apply_transformation(rgb, mask, regions, cfg_none)
    eff_mask = meta_none["effective_target_mask"]

    eval_rep = EVALUATION_ENGINE.evaluate(rgb, out_none, eff_mask, regions, cfg_none)
    keys = [c.transform_key for c in eval_rep.controlled_transforms]
    assert keys == ["jpeg_q75", "resize_0_5x", "gaussian_blur_3x3"]
    assert all("." not in k for k in keys)

    png_bytes = SECURITY_ENGINE.encode_and_sanitize_png(out_none)
    sec_audit = SECURITY_ENGINE.verify_png_bytes(png_bytes, input_sha256="abc")

    audit_rep = AUDIT_ENGINE.generate_audit_report(
        session_id="test_sess",
        original_rgb=rgb,
        transformed_rgb=out_none,
        effective_target_mask=eff_mask,
        resolved_regions=regions,
        config=cfg_none,
        security_audit=sec_audit,
        evaluation_report=eval_rep,
    )
    # Must NOT pass when method is 'none'
    assert audit_rep.overall_audit_status == "WARN"
    assert audit_rep.checks["transformation_execution"] == "WARN"


def test_png_metadata_sanitisation_and_crc32() -> None:
    """Verifies that exported PNGs contain only IHDR, IDAT, IEND with valid CRC32 checksums."""
    rgb = _create_synthetic_rgb(128, 128)
    clean_png = SECURITY_ENGINE.encode_and_sanitize_png(rgb)
    audit = SECURITY_ENGINE.verify_png_bytes(clean_png, input_sha256="deadbeef")

    assert audit.is_clean_png is True
    assert audit.all_crc32_valid is True
    assert audit.forbidden_metadata_chunks_found == []
    assert set(audit.chunks_present).issubset({"IHDR", "IDAT", "IEND"})


def test_fastapi_end_to_end_workflow() -> None:
    """Tests the complete API workflow: upload -> region update -> execute -> export -> purge."""
    client = TestClient(app)

    rgb = _create_synthetic_rgb(300, 220)
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    assert ok

    # 1. Upload & analyse
    up_res = client.post(
        "/api/sessions/upload",
        files={"file": ("synthetic.png", buf.tobytes(), "image/png")},
        data={"auto_resize": "true"},
    )
    assert up_res.status_code == 200
    up_data = up_res.json()
    session_id = up_data["session_id"]

    # 2. Add a manual region
    reg_res = client.put(
        f"/api/sessions/{session_id}/regions",
        json={
            "active_region_ids": ["manual_001"],
            "excluded_region_ids": [],
            "manual_regions": [
                {"region_id": "manual_001", "category": "manual", "x1": 20, "y1": 20, "x2": 120, "y2": 120, "active": True}
            ],
        },
    )
    assert reg_res.status_code == 200

    # 3. Execute VIGIL transformation
    exec_res = client.post(
        "/api/vigil/execute",
        json={
            "session_id": session_id,
            "config": {
                "policy_id": "policy_strict",
                "method": "gaussian_noise",
                "noise_sigma": 22.0,
                "random_seed": 42,
                "manual_regions": [
                    {"region_id": "manual_001", "category": "manual", "x1": 20, "y1": 20, "x2": 120, "y2": 120, "active": True}
                ],
            },
            "run_evaluation": True,
        },
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["audit_report"]["active_protected_regions"] >= 1
    assert exec_data["audit_report"]["modified_pixels_within_target_ratio"] > 0.90

    # 4. Export PNG, JSON, and ZIP
    png_res = client.get(f"/api/export/{session_id}/image.png")
    assert png_res.status_code == 200
    assert png_res.headers["content-type"] == "image/png"

    json_res = client.get(f"/api/export/{session_id}/audit.json")
    assert json_res.status_code == 200

    zip_res = client.get(f"/api/export/{session_id}/bundle.zip")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # 5. Purge session
    del_res = client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["purged"] is True
