"""Active VIGIL runtime tests.

Covers the committed TorchScript weights, the source architecture, fallback
reporting, mask exclusion, seeded Gaussian noise, structured-frequency
perturbation, composite redaction, honest auditing, PNG sanitisation and the
Citizen-mounted HTTP workflow. Local privacy efficacy remains UNMEASURED.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.citizen.api import build_app
from packages.vigil.config import DEFAULT_WEIGHTS_CANDIDATES
from packages.vigil.engines.audit_engine import AUDIT_ENGINE
from packages.vigil.engines.evaluation_engine import EVALUATION_ENGINE
from packages.vigil.engines.privacy_engine import PRIVACY_ENGINE
from packages.vigil.engines.security_engine import SECURITY_ENGINE
from packages.vigil.models.privacy_net import LazyModelManager, MODEL_MANAGER, VigilPrivacyNet
from packages.vigil.schemas import BoundingBox, DetectedRegion, TransformationConfig
from tools.check_vigil_assets import main as check_weight_assets

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "packages" / "vigil" / "model_manifest.json"


def _synthetic_rgb(width: int = 320, height: int = 240) -> np.ndarray:
    rng = np.random.default_rng(12345)
    image = rng.integers(40, 210, size=(height, width, 3), dtype=np.uint8)
    for x in range(30, min(180, width - 10), 12):
        cv2.rectangle(image, (x, max(0, height - 60)), (x + 6, height - 35),
                      (250, 250, 250), -1)
    return image


def _region(region_id: str, category: str, box: tuple[int, int, int, int],
            active: bool = True) -> DetectedRegion:
    return DetectedRegion(
        region_id=region_id,
        category=category,  # type: ignore[arg-type]
        bbox=BoundingBox(x1=box[0], y1=box[1], x2=box[2], y2=box[3]),
        confidence=0.92,
        detector_source="synthetic_test",
        active=active,
    )


def test_torchscript_weights_are_active_and_manifest_matches() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = manifest["artifacts"]["torchscript_deployment_model"]
    active = manifest["active_deployment_model"]
    assert check_weight_assets([]) == 0
    assert DEFAULT_WEIGHTS_CANDIDATES[0].name == active["filename"] == entry["filename"]

    status = MODEL_MANAGER.get_status()
    assert status["system_mode"] == "NEURAL_WEIGHTS_ACTIVE"
    assert status["is_neural_active"] is True
    assert status["architecture"] == "TorchScript_VigilPrivacyNet"
    assert status["weights_file"] == entry["filename"]
    assert status["weights_sha256"] == entry["sha256"].split(":", 1)[1]
    assert status["weights_byte_size"] == entry["size_bytes"]
    assert status["parameter_count"] == 4_428_047
    assert status["under_100m_limit"] is True


def test_source_architecture_and_explicit_fallback(tmp_path: Path) -> None:
    source_model = VigilPrivacyNet(num_classes=7, pretrained_backbone=False)
    source_params = sum(p.numel() for p in source_model.parameters())
    assert source_params == 6_394_127
    assert source_params < 100_000_000

    empty = tmp_path / "empty.pt"
    empty.write_bytes(b"")
    fallback = LazyModelManager(candidate_paths=[empty]).get_status()
    assert fallback["system_mode"] == "FALLBACK_HEURISTIC_MODE"
    assert fallback["is_neural_active"] is False
    assert fallback["weights_sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_privacy_mask_exclusion_logic() -> None:
    height, width = 200, 300
    segmentation = np.zeros((height, width), dtype=np.uint8)
    segmentation[20:100, 20:100] = 1
    segmentation[20:100, 180:260] = 1
    regions = [
        _region("reg_001", "face", (20, 20, 100, 100), True),
        _region("reg_002", "face", (180, 20, 260, 100), False),
    ]
    config = TransformationConfig(
        policy_id="policy_strict", method="solid",
        excluded_region_ids=["reg_002"], mask_dilation_px=0,
    )
    mask, _ = PRIVACY_ENGINE.build_protection_mask((height, width), regions, segmentation, config)
    assert np.all(mask[30:90, 30:90] == 1)
    assert np.all(mask[20:100, 180:260] == 0)


def test_seeded_gaussian_noise_reproducibility_and_isolation() -> None:
    rgb = _synthetic_rgb(200, 200)
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[50:150, 50:150] = 1
    config = TransformationConfig(
        method="gaussian_noise", noise_sigma=25.0, random_seed=999,
        apply_noise_to="selected_regions", mask_dilation_px=0,
    )
    first, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, [], config)
    second, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, [], config)
    assert np.array_equal(first, second)
    assert np.array_equal(first[:40, :40], rgb[:40, :40])
    assert not np.array_equal(first[50:150, 50:150], rgb[50:150, 50:150])


def test_structured_frequency_perturbation_reproducibility_and_isolation() -> None:
    rgb = _synthetic_rgb(200, 200)
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[50:150, 50:150] = 1
    config = TransformationConfig(
        method="structured_freq", freq_strength=16.0, random_seed=999,
        apply_noise_to="selected_regions", mask_dilation_px=0,
    )
    first, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, [], config)
    second, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, [], config)
    assert np.array_equal(first, second)
    assert np.array_equal(first[:40, :40], rgb[:40, :40])
    assert not np.array_equal(first[50:150, 50:150], rgb[50:150, 50:150])


def test_composite_redaction_hard_pixelates_sensitive_text_and_soft_noise_elsewhere() -> None:
    rgb = _synthetic_rgb(200, 200)
    mask = np.zeros((200, 200), dtype=np.uint8)
    mask[30:80, 30:80] = 1
    mask[110:170, 110:170] = 1
    regions = [
        _region("qr_001", "qr_code", (30, 30, 80, 80), True),
        _region("face_001", "face", (110, 120, 170, 170), True),
    ]
    config = TransformationConfig(
        method="composite_redact_and_noise", pixel_block_size=10,
        noise_sigma=22.0, random_seed=123, apply_noise_to="selected_regions",
        mask_dilation_px=0,
    )
    output, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, regions, config)
    pixelated = PRIVACY_ENGINE._apply_pixelation(rgb, config.pixel_block_size)
    assert np.array_equal(output[30:80, 30:80], pixelated[30:80, 30:80])
    assert not np.array_equal(output[110:170, 110:170], rgb[110:170, 110:170])
    assert np.array_equal(output[:20, :20], rgb[:20, :20])


def test_evaluation_keys_and_honest_audit() -> None:
    rgb = _synthetic_rgb(240, 240)
    mask = np.zeros((240, 240), dtype=np.uint8)
    mask[40:120, 40:120] = 1
    regions = [_region("reg_001", "face", (40, 40, 120, 120), True)]
    config = TransformationConfig(method="none", mask_dilation_px=0)
    output, metadata = PRIVACY_ENGINE.apply_transformation(rgb, mask, regions, config)
    effective_mask = metadata["effective_target_mask"]
    evaluation = EVALUATION_ENGINE.evaluate(rgb, output, effective_mask, regions, config)
    keys = [item.transform_key for item in evaluation.controlled_transforms]
    assert keys == ["jpeg_q75", "resize_0_5x", "gaussian_blur_3x3"]
    assert all("." not in key for key in keys)

    png = SECURITY_ENGINE.encode_and_sanitize_png(output)
    security_audit = SECURITY_ENGINE.verify_png_bytes(png, input_sha256="abc")
    audit = AUDIT_ENGINE.generate_audit_report(
        session_id="test_sess", original_rgb=rgb, transformed_rgb=output,
        effective_target_mask=effective_mask, resolved_regions=regions,
        config=config, security_audit=security_audit,
        evaluation_report=evaluation,
    )
    assert audit.overall_audit_status == "WARN"
    assert audit.checks["transformation_execution"] == "WARN"


def test_png_metadata_sanitisation_and_crc32() -> None:
    rgb = _synthetic_rgb(128, 128)
    png = SECURITY_ENGINE.encode_and_sanitize_png(rgb)
    audit = SECURITY_ENGINE.verify_png_bytes(png, input_sha256="deadbeef")
    assert audit.is_clean_png is True
    assert audit.all_crc32_valid is True
    assert audit.forbidden_metadata_chunks_found == []
    assert set(audit.chunks_present).issubset({"IHDR", "IDAT", "IEND"})


def test_citizen_mounted_fastapi_end_to_end_workflow() -> None:
    client = TestClient(build_app(bus_url=""))
    assert client.get("/vigil/", follow_redirects=False).status_code == 200
    assert client.get("/vigil/static/app.js").status_code == 200
    overview = client.get("/vigil/api/overview")
    assert overview.status_code == 200
    assert overview.json()["model_status"]["is_neural_active"] is True

    rgb = _synthetic_rgb(300, 220)
    ok, encoded = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    assert ok
    upload = client.post(
        "/vigil/api/sessions/upload",
        files={"file": ("synthetic.png", encoded.tobytes(), "image/png")},
        data={"auto_resize": "true"},
    )
    assert upload.status_code == 200, upload.text
    sid = upload.json()["session_id"]

    manual = {
        "region_id": "manual_001", "category": "manual",
        "x1": 20, "y1": 20, "x2": 120, "y2": 120, "active": True,
    }
    update = client.put(
        f"/vigil/api/sessions/{sid}/regions",
        json={"active_region_ids": ["manual_001"], "excluded_region_ids": [],
              "manual_regions": [manual]},
    )
    assert update.status_code == 200, update.text

    execution = client.post(
        "/vigil/api/vigil/execute",
        json={
            "session_id": sid,
            "config": {
                "policy_id": "policy_strict", "method": "gaussian_noise",
                "noise_sigma": 22.0, "random_seed": 42,
                "apply_noise_to": "selected_regions", "mask_dilation_px": 0,
                "active_region_ids": ["manual_001"], "manual_regions": [manual],
            },
            "run_evaluation": True,
        },
    )
    assert execution.status_code == 200, execution.text
    report = execution.json()
    assert report["audit_report"]["active_protected_regions"] >= 1
    assert report["audit_report"]["modified_pixels_within_target_ratio"] > 0.90
    assert report["transformed_png_url"].startswith("data:image/png;base64,")

    assert client.get(f"/vigil/api/export/{sid}/image.png").status_code == 200
    assert client.get(f"/vigil/api/export/{sid}/audit.json").status_code == 200
    assert client.get(f"/vigil/api/export/{sid}/bundle.zip").status_code == 200
    deleted = client.delete(f"/vigil/api/sessions/{sid}")
    assert deleted.status_code == 200 and deleted.json()["purged"] is True


@pytest.mark.parametrize("method", ["gaussian_noise", "structured_freq", "composite_redact_and_noise"])
def test_transformation_methods_are_deterministic(method: str) -> None:
    rgb = _synthetic_rgb(120, 120)
    mask = np.zeros((120, 120), dtype=np.uint8)
    mask[20:90, 20:90] = 1
    regions = [_region("text_001", "text", (20, 20, 90, 90), True)]
    config = TransformationConfig(method=method, random_seed=7, mask_dilation_px=0)  # type: ignore[arg-type]
    first, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, regions, config)
    second, _ = PRIVACY_ENGINE.apply_transformation(rgb, mask, regions, config)
    assert np.array_equal(first, second)
