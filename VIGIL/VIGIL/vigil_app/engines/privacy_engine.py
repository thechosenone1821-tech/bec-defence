# vigil_app/engines/privacy_engine.py
"""
VIGIL Privacy Engine
Handles policy application, manual region correction, fixed region-exclusion mask logic,
and deterministic/reproducible privacy transformations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

from vigil_app.config import PROTECTION_POLICIES
from vigil_app.schemas import (
    BoundingBox,
    DetectedRegion,
    ManualRegionInput,
    TransformationConfig,
)


class PrivacyEngine:
    """Constructs accurate protection masks and executes configured privacy transformations."""

    @staticmethod
    def merge_manual_regions(
        detected_regions: List[DetectedRegion],
        manual_inputs: List[ManualRegionInput],
        image_shape: Tuple[int, int],
    ) -> List[DetectedRegion]:
        h, w = image_shape[:2]
        merged: List[DetectedRegion] = [r.model_copy(deep=True) for r in detected_regions]

        for idx, m in enumerate(manual_inputs, start=1):
            x1 = int(np.clip(min(m.x1, m.x2), 0, w - 1))
            y1 = int(np.clip(min(m.y1, m.y2), 0, h - 1))
            x2 = int(np.clip(max(m.x1, m.x2), 0, w))
            y2 = int(np.clip(max(m.y1, m.y2), 0, h))
            if x2 - x1 < 4 or y2 - y1 < 4:
                continue

            reg_id = m.region_id or f"manual_{idx:03d}"
            existing_idx = next((i for i, r in enumerate(merged) if r.region_id == reg_id), None)
            manual_region = DetectedRegion(
                region_id=reg_id,
                category=m.category,
                bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                confidence=1.0,
                detector_source="User_Manual_Annotation",
                active=m.active,
                semantic_classes_present=[],
                notes="Manually added/corrected region",
            )
            if existing_idx is not None:
                merged[existing_idx] = manual_region
            else:
                merged.append(manual_region)

        return merged

    @classmethod
    def resolve_active_regions(
        cls,
        regions: List[DetectedRegion],
        config: TransformationConfig,
    ) -> List[DetectedRegion]:
        policy = PROTECTION_POLICIES.get(config.policy_id, PROTECTION_POLICIES["policy_strict"])
        excluded_set = set(config.excluded_region_ids)
        active_override_set = (
            set(config.active_region_ids) if config.active_region_ids is not None else None
        )

        resolved: List[DetectedRegion] = []
        for reg in regions:
            r_copy = reg.model_copy(deep=True)
            if r_copy.region_id in excluded_set:
                r_copy.active = False
            elif active_override_set is not None:
                r_copy.active = r_copy.region_id in active_override_set
            else:
                r_copy.active = bool(r_copy.active and (r_copy.category in policy.target_categories))
            resolved.append(r_copy)

        return resolved

    @classmethod
    def build_protection_mask(
        cls,
        image_shape: Tuple[int, int],
        regions: List[DetectedRegion],
        seg_mask: np.ndarray,
        config: TransformationConfig,
    ) -> Tuple[np.ndarray, List[DetectedRegion]]:
        """
        Builds a binary protection mask M in {0, 1}^(H x W) with fixed exclusion logic.
        """
        h, w = image_shape[:2]
        resolved_regions = cls.resolve_active_regions(regions, config)
        mask = np.zeros((h, w), dtype=np.uint8)

        active_classes = [int(c) for c in config.active_semantic_classes if 1 <= int(c) <= 6]

        # Step 1: Apply active non-manual regions
        for reg in resolved_regions:
            if not reg.active or reg.category == "manual":
                continue
            x1, y1, x2, y2 = reg.bbox.x1, reg.bbox.y1, reg.bbox.x2, reg.bbox.y2
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            if reg.category == "face":
                roi_seg = seg_mask[y1:y2, x1:x2]
                if active_classes and np.any(np.isin(roi_seg, active_classes)):
                    class_hits = np.isin(roi_seg, active_classes).astype(np.uint8)
                    mask[y1:y2, x1:x2] = np.maximum(mask[y1:y2, x1:x2], class_hits)
                elif not active_classes:
                    pass
                else:
                    mask[y1:y2, x1:x2] = 1
            else:
                mask[y1:y2, x1:x2] = 1

        # Step 2: Explicit exclusion carve-out (Bug Fix #3)
        for reg in resolved_regions:
            if not reg.active:
                x1, y1 = max(0, reg.bbox.x1), max(0, reg.bbox.y1)
                x2, y2 = min(w, reg.bbox.x2), min(h, reg.bbox.y2)
                if x2 > x1 and y2 > y1:
                    mask[y1:y2, x1:x2] = 0

        # Step 3: Re-assert active regions + apply active manual regions on top
        for reg in resolved_regions:
            if not reg.active:
                continue
            x1, y1 = max(0, reg.bbox.x1), max(0, reg.bbox.y1)
            x2, y2 = min(w, reg.bbox.x2), min(h, reg.bbox.y2)
            if x2 <= x1 or y2 <= y1:
                continue
            if reg.category == "manual" or reg.category != "face":
                mask[y1:y2, x1:x2] = 1
            elif reg.category == "face" and active_classes:
                roi_seg = seg_mask[y1:y2, x1:x2]
                if np.any(np.isin(roi_seg, active_classes)):
                    mask[y1:y2, x1:x2] = np.maximum(
                        mask[y1:y2, x1:x2],
                        np.isin(roi_seg, active_classes).astype(np.uint8),
                    )
                else:
                    mask[y1:y2, x1:x2] = 1

        # Step 4: Optional morphological dilation
        if config.mask_dilation_px > 0 and np.any(mask > 0):
            k = int(config.mask_dilation_px) * 2 + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
            mask = cv2.dilate(mask, kernel, iterations=1)
            for reg in resolved_regions:
                if not reg.active:
                    x1, y1 = max(0, reg.bbox.x1), max(0, reg.bbox.y1)
                    x2, y2 = min(w, reg.bbox.x2), min(h, reg.bbox.y2)
                    mask[y1:y2, x1:x2] = 0
            for reg in resolved_regions:
                if reg.active and reg.category == "manual":
                    x1, y1 = max(0, reg.bbox.x1), max(0, reg.bbox.y1)
                    x2, y2 = min(w, reg.bbox.x2), min(h, reg.bbox.y2)
                    mask[y1:y2, x1:x2] = 1

        return mask, resolved_regions

    @staticmethod
    def _apply_pixelation(rgb: np.ndarray, block_size: int) -> np.ndarray:
        h, w = rgb.shape[:2]
        b = max(2, int(block_size))
        small_w = max(1, w // b)
        small_h = max(1, h // b)
        down = cv2.resize(rgb, (small_w, small_h), interpolation=cv2.INTER_AREA)
        return cv2.resize(down, (w, h), interpolation=cv2.INTER_NEAREST)

    @staticmethod
    def _apply_blur(rgb: np.ndarray, kernel_size: int) -> np.ndarray:
        k = max(3, int(kernel_size))
        if k % 2 == 0:
            k += 1
        return cv2.GaussianBlur(rgb, (k, k), sigmaX=0)

    @staticmethod
    def _apply_solid(rgb: np.ndarray, color_rgb: List[int]) -> np.ndarray:
        canvas = np.empty_like(rgb)
        r = int(np.clip(color_rgb[0] if len(color_rgb) > 0 else 24, 0, 255))
        g = int(np.clip(color_rgb[1] if len(color_rgb) > 1 else 24, 0, 255))
        b = int(np.clip(color_rgb[2] if len(color_rgb) > 2 else 24, 0, 255))
        canvas[:, :] = (r, g, b)
        return canvas

    @staticmethod
    def _generate_seeded_gaussian_noise(
        shape: Tuple[int, int, int],
        sigma: float,
        seed: int,
    ) -> np.ndarray:
        rng = np.random.default_rng(int(seed))
        return rng.normal(loc=0.0, scale=float(sigma), size=shape).astype(np.float32)

    @staticmethod
    def _generate_structured_freq_perturbation(
        shape: Tuple[int, int, int],
        strength: float,
        seed: int,
    ) -> np.ndarray:
        """Reproducible mid-frequency spatial carrier + phase-shifted sinusoid."""
        h, w, c = shape
        rng = np.random.default_rng(int(seed))
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

        perturbation = np.zeros((h, w, c), dtype=np.float32)
        for ch in range(c):
            phase_x = float(rng.uniform(0, 2 * np.pi))
            phase_y = float(rng.uniform(0, 2 * np.pi))
            freq_1 = np.sin(2.0 * np.pi * xx / 6.0 + phase_x) * np.cos(2.0 * np.pi * yy / 6.0 + phase_y)
            freq_2 = np.cos(2.0 * np.pi * (xx + yy) / 4.0 - phase_x)
            jitter = rng.normal(0.0, 0.25, size=(h, w)).astype(np.float32)
            perturbation[:, :, ch] = float(strength) * (0.65 * freq_1 + 0.35 * freq_2 + jitter)

        return perturbation

    @classmethod
    def apply_transformation(
        cls,
        rgb_image: np.ndarray,
        protection_mask: np.ndarray,
        resolved_regions: List[DetectedRegion],
        config: TransformationConfig,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Applies the selected VIGIL privacy transformation according to `config`."""
        h, w = rgb_image.shape[:2]
        out = rgb_image.copy()
        mask_bool = protection_mask > 0
        mask_3d = mask_bool[:, :, None]

        method = config.method
        applied_target_mask = mask_bool.copy()

        if method == "none":
            applied_target_mask = np.zeros((h, w), dtype=bool)

        elif method == "solid":
            solid_layer = cls._apply_solid(rgb_image, config.solid_color_rgb)
            out = np.where(mask_3d, solid_layer, rgb_image)

        elif method == "pixelate":
            pix_layer = cls._apply_pixelation(rgb_image, config.pixel_block_size)
            out = np.where(mask_3d, pix_layer, rgb_image)

        elif method == "blur":
            blur_layer = cls._apply_blur(rgb_image, config.blur_kernel_size)
            out = np.where(mask_3d, blur_layer, rgb_image)

        elif method in ("gaussian_noise", "structured_freq"):
            if method == "gaussian_noise":
                delta = cls._generate_seeded_gaussian_noise(
                    rgb_image.shape, sigma=config.noise_sigma, seed=config.random_seed
                )
            else:
                delta = cls._generate_structured_freq_perturbation(
                    rgb_image.shape, strength=config.freq_strength, seed=config.random_seed
                )

            if config.apply_noise_to == "full_image":
                target_bool = np.ones((h, w), dtype=bool)
            elif config.apply_noise_to == "unredacted_background":
                target_bool = ~mask_bool
            else:
                target_bool = mask_bool

            applied_target_mask = target_bool
            target_3d = target_bool[:, :, None].astype(np.float32)
            out = np.clip(rgb_image.astype(np.float32) + target_3d * delta, 0, 255).astype(np.uint8)

        elif method == "composite_redact_and_noise":
            pix_layer = cls._apply_pixelation(rgb_image, config.pixel_block_size)
            hard_redact_mask = np.zeros((h, w), dtype=bool)
            for reg in resolved_regions:
                if reg.active and reg.category in ("qr_code", "text", "licence_plate"):
                    hard_redact_mask[reg.bbox.y1 : reg.bbox.y2, reg.bbox.x1 : reg.bbox.x2] = True

            soft_noise_mask = mask_bool & (~hard_redact_mask)
            delta = cls._generate_seeded_gaussian_noise(
                rgb_image.shape, sigma=config.noise_sigma, seed=config.random_seed
            )
            noisy_img = np.clip(
                rgb_image.astype(np.float32) + soft_noise_mask[:, :, None].astype(np.float32) * delta,
                0,
                255,
            ).astype(np.uint8)
            out = np.where(hard_redact_mask[:, :, None], pix_layer, noisy_img)
            applied_target_mask = mask_bool

        # Optional visible attribution watermark
        if config.apply_visible_watermark:
            out = out.copy()
            wm_text = "VIGIL PRIVACY TRANSFORM"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(wm_text, font, 0.45, 1)
            pad = 8
            x_box = max(0, w - tw - pad * 2 - 6)
            y_box = max(0, h - th - pad * 2 - 6)
            overlay = out.copy()
            cv2.rectangle(overlay, (x_box, y_box), (w - 6, h - 6), (18, 22, 28), -1)
            cv2.addWeighted(overlay, 0.72, out, 0.28, 0, out)
            cv2.putText(
                out,
                wm_text,
                (x_box + pad, h - pad - 6),
                font,
                0.45,
                (220, 228, 236),
                1,
                cv2.LINE_AA,
            )

        meta: Dict[str, Any] = {
            "method": method,
            "policy_id": config.policy_id,
            "random_seed": config.random_seed,
            "target_pixel_count": int(np.count_nonzero(applied_target_mask)),
            "total_pixel_count": int(h * w),
            "target_pixel_ratio": round(float(np.mean(applied_target_mask)), 6),
            # NOTE: vigil_core pops this numpy array out before serializing meta to JSON.
            "effective_target_mask": applied_target_mask,
        }
        return out, meta


PRIVACY_ENGINE = PrivacyEngine()
