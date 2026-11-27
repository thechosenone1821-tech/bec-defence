# packages/vigil/engines/audit_engine.py
"""
VIGIL Audit Engine
Generates transparent, reproducible, machine-readable JSON audit reports.
Distinguishes pixel modification from detector suppression and visual quality.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import uuid
from typing import Any, Dict, List, Optional

import numpy as np

from packages.vigil.models.privacy_net import MODEL_MANAGER
from packages.vigil.schemas import (
    AuditReport,
    DetectedRegion,
    EvaluationReport,
    PngSecurityAudit,
    TransformationConfig,
)


class AuditEngine:
    """Produces verifiable audit reports without inflating privacy claims."""

    @staticmethod
    def build_integrity_manifest(
        session_id: str,
        input_sha256: str,
        output_sha256: str,
        config: TransformationConfig,
        model_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload: Dict[str, Any] = {
            "manifest_type": "VIGIL_Reproducibility_And_Integrity_Manifest_v2",
            "session_id": session_id,
            "timestamp_utc": timestamp,
            "input_image_sha256": input_sha256,
            "output_png_sha256": output_sha256,
            "model_architecture": model_info.get("architecture"),
            "model_weights_sha256": model_info.get("weights_sha256"),
            "system_mode": model_info.get("system_mode"),
            "transformation_parameters": config.model_dump(),
            "cryptographic_scope_notice": (
                "This manifest records deterministic SHA-256 digests and transformation parameters "
                "for experiment reproducibility. It is signed with a local session HMAC key and does "
                "not constitute a third-party X.509 C2PA hardware-attested certificate."
            ),
        }
        canonical = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        local_key = hashlib.sha256(f"vigil_local_integrity:{session_id}".encode("utf-8")).digest()
        signature = hmac.new(local_key, canonical, hashlib.sha256).hexdigest()
        payload["local_hmac_sha256"] = signature
        return payload

    @classmethod
    def generate_audit_report(
        cls,
        session_id: str,
        original_rgb: np.ndarray,
        transformed_rgb: np.ndarray,
        effective_target_mask: np.ndarray,
        resolved_regions: List[DetectedRegion],
        config: TransformationConfig,
        security_audit: PngSecurityAudit,
        evaluation_report: Optional[EvaluationReport],
    ) -> AuditReport:
        model_info = MODEL_MANAGER.get_status()
        system_mode = model_info["system_mode"]

        total_detected = len(resolved_regions)
        active_regions = [r for r in resolved_regions if r.active]
        excluded_regions = [r for r in resolved_regions if not r.active]

        target_bool = effective_target_mask > 0
        non_target_bool = ~target_bool

        pixel_max_diff = np.max(
            np.abs(transformed_rgb.astype(np.int16) - original_rgb.astype(np.int16)),
            axis=2,
        )

        target_pixel_ratio = round(float(np.mean(target_bool)), 6)
        if np.any(target_bool):
            modified_within_target = round(float(np.mean(pixel_max_diff[target_bool] >= 1)), 6)
        else:
            modified_within_target = 0.0

        if np.any(non_target_bool):
            bg_mask = non_target_bool.copy()
            if config.apply_visible_watermark:
                h, w = bg_mask.shape[:2]
                bg_mask[max(0, h - 45) : h, max(0, w - 260) : w] = False
            unintended_bg_mod = (
                round(float(np.mean(pixel_max_diff[bg_mask] >= 1)), 6)
                if np.any(bg_mask)
                else 0.0
            )
        else:
            unintended_bg_mod = 0.0

        checks: Dict[str, str] = {}
        reasons: List[str] = []

        # Check 1: PNG Metadata & Chunk Integrity
        if security_audit.is_clean_png and security_audit.all_crc32_valid:
            checks["png_metadata_sanitisation"] = "PASS"
        else:
            checks["png_metadata_sanitisation"] = "FAIL"
            reasons.append("PNG binary verification failed or forbidden metadata chunks remained.")

        # Check 2: Unintended Background Modification Isolation
        if unintended_bg_mod == 0.0:
            checks["background_isolation"] = "PASS"
        else:
            checks["background_isolation"] = "WARN"
            reasons.append(
                f"Non-target background pixels showed modification ratio {unintended_bg_mod:.4f}."
            )

        # Check 3: Target Region Pixel Transformation Execution
        if config.method == "none":
            checks["transformation_execution"] = "WARN"
            reasons.append("Transformation method is 'none'; sensitive regions remain unmodified.")
        elif len(active_regions) == 0 and config.apply_noise_to == "selected_regions":
            checks["transformation_execution"] = "WARN"
            reasons.append("No active regions were selected for transformation.")
        elif modified_within_target >= 0.90:
            checks["transformation_execution"] = "PASS"
        elif modified_within_target > 0.0:
            checks["transformation_execution"] = "WARN"
            reasons.append(
                f"Only {modified_within_target * 100:.1f}% of target mask pixels changed by >= 1 intensity unit."
            )
        else:
            checks["transformation_execution"] = "FAIL"
            reasons.append("0% of target mask pixels were modified despite an active transformation method.")

        # Check 4: Empirical Local Detector Suppression
        if evaluation_report is not None:
            retained_any = [
                d for d in evaluation_report.detector_retention if d.matched_regions_after > 0
            ]
            active_cats_before = [
                d for d in evaluation_report.detector_retention if d.count_before > 0
            ]
            if not active_cats_before:
                checks["local_detector_suppression"] = "NOT_APPLICABLE"
            elif len(retained_any) == 0:
                checks["local_detector_suppression"] = "PASS"
            else:
                checks["local_detector_suppression"] = "WARN"
                for d in retained_any:
                    reasons.append(
                        f"Local detector '{d.detector_name}' still re-detected "
                        f"{d.matched_regions_after}/{d.count_before} active '{d.category}' region(s) after transformation."
                    )
        else:
            checks["local_detector_suppression"] = "SKIPPED"

        # Check 5: Neural Weights vs Fallback Mode Transparency
        if system_mode == "NEURAL_WEIGHTS_ACTIVE":
            checks["segmentation_model_mode"] = "PASS"
        else:
            checks["segmentation_model_mode"] = "WARN"
            reasons.append(
                "Application is running in FALLBACK_HEURISTIC_MODE because no loadable VIGIL checkpoint was found. "
                "Facial semantic sub-regions use geometric priors rather than trained neural weights."
            )

        # Determine overall status honestly
        if "FAIL" in checks.values():
            overall_status = "FAIL"
        elif "WARN" in checks.values():
            overall_status = "WARN"
        else:
            overall_status = "PASS"

        if not reasons:
            reasons.append(
                "All selected target regions were transformed, local detectors reported 0 re-detections, "
                "and PNG metadata sanitisation passed."
            )

        limitations = [
            "Pixel modification coverage measures whether target pixels changed numerically; it does not guarantee anonymity.",
            "Local detector suppression tests OpenCV Haar cascades, QR decoding, and morphological text contours only.",
            "Deep facial recognition embedding distance (ArcFace/AdaFace) and diffusion inpainting benchmarks are UNAVAILABLE in this CPU-only 8 GB RAM build.",
        ]
        if system_mode == "FALLBACK_HEURISTIC_MODE":
            limitations.insert(
                0,
                "FALLBACK MODE ACTIVE: no loadable VIGIL neural checkpoint was found. "
                "Semantic face parsing is currently approximated via geometric ellipses inside detected face boxes.",
            )

        manifest = cls.build_integrity_manifest(
            session_id=session_id,
            input_sha256=security_audit.input_sha256,
            output_sha256=security_audit.output_sha256,
            config=config,
            model_info=model_info,
        )

        return AuditReport(
            audit_id=f"audit_{uuid.uuid4().hex[:12]}",
            timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            session_id=session_id,
            system_mode=system_mode,  # type: ignore[arg-type]
            model_info=model_info,
            transformation_config=config,
            total_detected_regions=total_detected,
            active_protected_regions=len(active_regions),
            excluded_regions_count=len(excluded_regions),
            target_mask_pixel_ratio=target_pixel_ratio,
            modified_pixels_within_target_ratio=modified_within_target,
            unintended_background_modification_ratio=unintended_bg_mod,
            security_verification=security_audit,
            evaluation_summary=evaluation_report,
            integrity_manifest=manifest,
            checks=checks,
            overall_audit_status=overall_status,  # type: ignore[arg-type]
            status_reasons=reasons,
            evaluation_limitations=limitations,
        )


AUDIT_ENGINE = AuditEngine()
