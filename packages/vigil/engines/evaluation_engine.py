# packages/vigil/engines/evaluation_engine.py
"""
VIGIL Evaluation Engine
Measures visual similarity (SSIM/PSNR), controlled transformation stability
(JPEG Q=75, Resize 0.5x, Gaussian 3x3), and empirical detector retention using
explicitly identified local detectors.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from packages.vigil.config import EVALUATION_TEST_REGISTRY
from packages.vigil.engines.perception_engine import PERCEPTION_ENGINE, _compute_iou
from packages.vigil.schemas import (
    ControlledTransformMetric,
    DetectedRegion,
    DetectorRetentionResult,
    EvaluationReport,
    TransformationConfig,
)


class VigilEvaluationEngine:
    """Executes reproducible, transparent image privacy and fidelity evaluations."""

    @staticmethod
    def compute_psnr(
        img_a: np.ndarray,
        img_b: np.ndarray,
        mask: Optional[np.ndarray] = None,
    ) -> float:
        diff = img_a.astype(np.float64) - img_b.astype(np.float64)
        if mask is not None:
            if not np.any(mask):
                return 99.0
            valid_diff = diff[mask > 0]
            mse = float(np.mean(np.square(valid_diff)))
        else:
            mse = float(np.mean(np.square(diff)))

        if mse <= 1e-10:
            return 99.0
        return round(float(10.0 * np.log10((255.0 ** 2) / mse)), 2)

    @staticmethod
    def compute_ssim(
        img_a: np.ndarray,
        img_b: np.ndarray,
        mask: Optional[np.ndarray] = None,
    ) -> float:
        """Computes Wang et al. (2004) SSIM on luminance; averages over mask if provided."""
        if mask is not None and not np.any(mask):
            return 1.0

        y_a = cv2.cvtColor(img_a, cv2.COLOR_RGB2GRAY).astype(np.float64)
        y_b = cv2.cvtColor(img_b, cv2.COLOR_RGB2GRAY).astype(np.float64)

        c1 = (0.01 * 255.0) ** 2
        c2 = (0.03 * 255.0) ** 2

        mu_a = cv2.GaussianBlur(y_a, (11, 11), 1.5)
        mu_b = cv2.GaussianBlur(y_b, (11, 11), 1.5)

        mu_a_sq = mu_a * mu_a
        mu_b_sq = mu_b * mu_b
        mu_ab = mu_a * mu_b

        sigma_a_sq = cv2.GaussianBlur(y_a * y_a, (11, 11), 1.5) - mu_a_sq
        sigma_b_sq = cv2.GaussianBlur(y_b * y_b, (11, 11), 1.5) - mu_b_sq
        sigma_ab = cv2.GaussianBlur(y_a * y_b, (11, 11), 1.5) - mu_ab

        numerator = (2.0 * mu_ab + c1) * (2.0 * sigma_ab + c2)
        denominator = (mu_a_sq + mu_b_sq + c1) * (sigma_a_sq + sigma_b_sq + c2)
        ssim_map = numerator / np.maximum(denominator, 1e-12)

        if mask is not None:
            val = float(np.mean(ssim_map[mask > 0]))
        else:
            val = float(np.mean(ssim_map))
        return round(float(np.clip(val, -1.0, 1.0)), 4)

    @staticmethod
    def _measure_detector_retention(
        transformed_rgb: np.ndarray,
        original_regions: List[DetectedRegion],
    ) -> List[DetectorRetentionResult]:
        """Re-runs the local PerceptionEngine detectors on `transformed_rgb`."""
        gray_after = cv2.cvtColor(transformed_rgb, cv2.COLOR_RGB2GRAY)

        after_faces = [b[:4] for b in PERCEPTION_ENGINE.detect_faces(gray_after)]
        after_qrs = [b[:4] for b in PERCEPTION_ENGINE.detect_qr_codes(transformed_rgb)]
        occupied = after_faces + after_qrs
        after_plates = [b[:4] for b in PERCEPTION_ENGINE.detect_licence_plates(gray_after, occupied)]
        occupied.extend(after_plates)
        after_texts = [b[:4] for b in PERCEPTION_ENGINE.detect_text_regions(gray_after, occupied)]

        category_map: Dict[str, Tuple[str, List[Tuple[int, int, int, int]]]] = {
            "face": ("OpenCV_Haar_Frontal+Profile_Cascade", after_faces),
            "qr_code": ("OpenCV_QRCodeDetector", after_qrs),
            "licence_plate": ("OpenCV_Haar_LicencePlate", after_plates),
            "text": ("Morphological_Gradient_TextDetector", after_texts),
        }

        retention_results: List[DetectorRetentionResult] = []
        for cat, (det_name, boxes_after) in category_map.items():
            orig_active_boxes = [
                (r.bbox.x1, r.bbox.y1, r.bbox.x2, r.bbox.y2)
                for r in original_regions
                if r.category == cat and r.active
            ]
            count_before = len(orig_active_boxes)
            count_after = len(boxes_after)

            matched = 0
            for ob in orig_active_boxes:
                if any(_compute_iou(ob, ab) >= 0.30 for ab in boxes_after):
                    matched += 1

            if count_before == 0:
                retained_ratio = 0.0
                note = f"No active '{cat}' regions were present prior to transformation."
            else:
                retained_ratio = round(float(matched / count_before), 4)
                if matched == 0:
                    note = (
                        f"0/{count_before} previously active '{cat}' regions were re-detected by {det_name}. "
                        "Note: suppression against this local detector does not prove resistance to deep neural models."
                    )
                else:
                    note = (
                        f"{matched}/{count_before} active '{cat}' regions were STILL detected by {det_name} "
                        "after transformation."
                    )

            retention_results.append(
                DetectorRetentionResult(
                    category=cat,
                    detector_name=det_name,
                    count_before=count_before,
                    count_after=count_after,
                    retained_ratio=retained_ratio,
                    matched_regions_after=matched,
                    status_note=note,
                )
            )

        return retention_results

    @classmethod
    def _run_controlled_transforms(
        cls,
        original_rgb: np.ndarray,
        transformed_rgb: np.ndarray,
        target_mask: np.ndarray,
    ) -> List[ControlledTransformMetric]:
        """Subjects `transformed_rgb` to JPEG Q=75, 0.5x resize, and 3x3 blur."""
        h, w = transformed_rgb.shape[:2]
        orig_f = original_rgb.astype(np.float32)
        trans_f = transformed_rgb.astype(np.float32)

        initial_delta = np.abs(trans_f - orig_f)
        if np.any(target_mask > 0):
            base_energy = float(np.mean(initial_delta[target_mask > 0]))
        else:
            base_energy = float(np.mean(initial_delta))

        # 1. JPEG Q=75
        bgr_trans = cv2.cvtColor(transformed_rgb, cv2.COLOR_RGB2BGR)
        ok, enc_buf = cv2.imencode(".jpg", bgr_trans, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if ok:
            jpeg_bgr = cv2.imdecode(enc_buf, cv2.IMREAD_COLOR)
            jpeg_rgb = cv2.cvtColor(jpeg_bgr, cv2.COLOR_BGR2RGB)
        else:
            jpeg_rgb = transformed_rgb.copy()

        # 2. Resize 0.5x -> 1.0x
        small = cv2.resize(transformed_rgb, (max(1, w // 2), max(1, h // 2)), interpolation=cv2.INTER_AREA)
        resize_rgb = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

        # 3. Gaussian Blur 3x3
        blur_rgb = cv2.GaussianBlur(transformed_rgb, (3, 3), sigmaX=0.8)

        variants = [
            ("jpeg_q75", "JPEG Compression (Quality = 75)", jpeg_rgb),
            ("resize_0_5x", "Spatial Resizing (0.5x Downscale + Upscale)", resize_rgb),
            ("gaussian_blur_3x3", "Gaussian Low-Pass Smoothing (3x3)", blur_rgb),
        ]

        results: List[ControlledTransformMetric] = []
        for key, label, var_rgb in variants:
            ssim_v = cls.compute_ssim(transformed_rgb, var_rgb)
            psnr_v = cls.compute_psnr(transformed_rgb, var_rgb)

            var_delta = np.abs(var_rgb.astype(np.float32) - orig_f)
            if np.any(target_mask > 0):
                surviving_energy = float(np.mean(var_delta[target_mask > 0]))
            else:
                surviving_energy = float(np.mean(var_delta))

            if base_energy <= 1e-5:
                retention_ratio = 0.0
            else:
                retention_ratio = round(float(np.clip(surviving_energy / base_energy, 0.0, 1.5)), 4)

            gray_var = cv2.cvtColor(var_rgb, cv2.COLOR_RGB2GRAY)
            faces_after = len(PERCEPTION_ENGINE.detect_faces(gray_var))

            interp = (
                f"Perturbation amplitude retention ratio = {retention_ratio:.2f}; "
                f"local Haar face detections post-{key} = {faces_after}. "
                "(Measures signal stability under image processing only, not biometric resistance.)"
            )
            results.append(
                ControlledTransformMetric(
                    transform_key=key,
                    transform_name=label,
                    ssim_vs_transformed=ssim_v,
                    psnr_vs_transformed_db=psnr_v,
                    perturbation_retention_ratio=retention_ratio,
                    post_transform_face_detections=faces_after,
                    interpretation=interp,
                )
            )

        return results

    @classmethod
    def evaluate(
        cls,
        original_rgb: np.ndarray,
        transformed_rgb: np.ndarray,
        target_mask: np.ndarray,
        resolved_regions: List[DetectedRegion],
        config: TransformationConfig,
    ) -> EvaluationReport:
        """Produces a complete, reproducible `EvaluationReport`."""
        mask_bool = target_mask > 0
        bg_mask_bool = ~mask_bool

        full_ssim = cls.compute_ssim(original_rgb, transformed_rgb)
        full_psnr = cls.compute_psnr(original_rgb, transformed_rgb)

        bg_ssim = cls.compute_ssim(original_rgb, transformed_rgb, mask=bg_mask_bool)
        bg_psnr = cls.compute_psnr(original_rgb, transformed_rgb, mask=bg_mask_bool)

        prot_ssim = cls.compute_ssim(original_rgb, transformed_rgb, mask=mask_bool)
        prot_psnr = cls.compute_psnr(original_rgb, transformed_rgb, mask=mask_bool)

        l1_diff = np.abs(transformed_rgb.astype(np.float32) - original_rgb.astype(np.float32))
        if np.any(mask_bool):
            prot_l1 = round(float(np.mean(l1_diff[mask_bool])), 3)
        else:
            prot_l1 = 0.0

        detector_retention = cls._measure_detector_retention(transformed_rgb, resolved_regions)
        controlled_transforms = cls._run_controlled_transforms(
            original_rgb, transformed_rgb, mask_bool
        )

        repro_payload = {
            "orig_sha256": hashlib.sha256(original_rgb.tobytes()).hexdigest(),
            "trans_sha256": hashlib.sha256(transformed_rgb.tobytes()).hexdigest(),
            "config": config.model_dump(),
        }
        repro_hash = hashlib.sha256(
            json.dumps(repro_payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        disclaimers = [
            "SSIM and PSNR measure visual similarity for human viewing; they do not measure biometric or identity protection.",
            "Pixel modification inside a region (L1 diff > 0) does not by itself constitute privacy protection.",
            "Detector retention tests evaluate only the listed local OpenCV/morphological detectors. A 0% retention rate on Haar cascades does not guarantee resistance against modern deep-learning facial recognition (e.g., ArcFace) or commercial OCR.",
            "JPEG Q=75 and 0.5x resize metrics measure signal survival under lossy compression and scaling, not resistance to deepfakes or adversarial recovery.",
        ]

        return EvaluationReport(
            experiment_id=f"exp_{repro_hash[:12]}",
            reproducibility_hash=repro_hash,
            random_seed=config.random_seed,
            full_image_ssim=full_ssim,
            full_image_psnr_db=full_psnr,
            unprotected_background_ssim=bg_ssim,
            unprotected_background_psnr_db=bg_psnr,
            protected_region_ssim=prot_ssim,
            protected_region_psnr_db=prot_psnr,
            protected_region_mean_l1_diff=prot_l1,
            detector_retention=detector_retention,
            controlled_transforms=controlled_transforms,
            test_registry=EVALUATION_TEST_REGISTRY,
            scientific_disclaimers=disclaimers,
        )


EVALUATION_ENGINE = VigilEvaluationEngine()
