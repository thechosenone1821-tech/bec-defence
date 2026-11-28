# packages/vigil/engines/vigil_core.py
"""
VIGIL Core Pipeline Orchestrator
Coordinates image ingestion, validation, preprocessing, perception, privacy
transformation, evaluation, security sanitisation, auditing, and export packaging.
"""

from __future__ import annotations

import base64
import gc
import hashlib
import io
import json
import time
import zipfile
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

from packages.vigil.config import HARDWARE_CONFIG, PROTECTION_POLICIES, SEMANTIC_CLASSES
from packages.vigil.engines.audit_engine import AUDIT_ENGINE
from packages.vigil.engines.evaluation_engine import EVALUATION_ENGINE
from packages.vigil.engines.perception_engine import PERCEPTION_ENGINE
from packages.vigil.engines.privacy_engine import PRIVACY_ENGINE
from packages.vigil.engines.security_engine import SECURITY_ENGINE, VigilSession
from packages.vigil.models.privacy_net import MODEL_MANAGER
from packages.vigil.schemas import (
    DetectedRegion,
    ManualRegionInput,
    TransformationConfig,
)

# Semantic class colormap (RGB) for diagnostic overlay
SEMANTIC_COLORMAP_RGB: Dict[int, Tuple[int, int, int]] = {
    1: (56, 189, 248),   # facial_skin: cyan-blue
    2: (250, 204, 21),   # eyes_and_eyebrows: amber
    3: (168, 85, 247),   # nose: purple
    4: (244, 63, 94),    # mouth_and_lips: rose
    5: (34, 197, 94),    # ears: emerald
    6: (249, 115, 22),   # hair_and_head: orange
}


class ImageValidationError(ValueError):
    """Raised when an uploaded file fails size, format, or resolution validation."""


class VigilCore:
    """Central processing pipeline for the VIGIL application."""

    @staticmethod
    def rgb_to_data_url(rgb_image: np.ndarray, quality: int = 88) -> str:
        bgr = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
        if not ok:
            raise RuntimeError("Failed to encode preview image.")
        b64 = base64.b64encode(buf.tobytes()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"

    @staticmethod
    def png_bytes_to_data_url(png_bytes: bytes) -> str:
        b64 = base64.b64encode(png_bytes).decode("ascii")
        return f"data:image/png;base64,{b64}"

    @classmethod
    def render_segmentation_overlay(
        cls,
        rgb_image: np.ndarray,
        seg_mask: np.ndarray,
    ) -> np.ndarray:
        overlay = rgb_image.copy()
        color_layer = np.zeros_like(rgb_image)
        fg_mask = seg_mask > 0
        for cls_id, color in SEMANTIC_COLORMAP_RGB.items():
            color_layer[seg_mask == cls_id] = color
        if np.any(fg_mask):
            blended = cv2.addWeighted(rgb_image, 0.55, color_layer, 0.45, 0)
            overlay[fg_mask] = blended[fg_mask]
        return overlay

    @classmethod
    def render_difference_heatmap(
        cls,
        original_rgb: np.ndarray,
        transformed_rgb: np.ndarray,
    ) -> np.ndarray:
        diff = np.abs(transformed_rgb.astype(np.int16) - original_rgb.astype(np.int16))
        mag = np.clip(np.mean(diff, axis=2) * 4.0, 0, 255).astype(np.uint8)
        heatmap_bgr = cv2.applyColorMap(mag, cv2.COLORMAP_INFERNO)
        return cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)

    @classmethod
    def ingest_and_analyze(
        cls,
        raw_bytes: bytes,
        filename: str,
        auto_resize: bool = True,
    ) -> Dict[str, Any]:
        """Workflow Steps 1 & 2: validate, decode, optionally downscale, run perception, store session."""
        if not raw_bytes:
            raise ImageValidationError("Uploaded file is empty (0 bytes).")
        if len(raw_bytes) > HARDWARE_CONFIG.max_upload_bytes:
            raise ImageValidationError(
                f"File size ({len(raw_bytes) / (1024 * 1024):.2f} MB) exceeds maximum limit "
                f"of {HARDWARE_CONFIG.max_upload_bytes // (1024 * 1024)} MB."
            )

        input_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        np_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ImageValidationError(
                "Unsupported or corrupted image file. Please upload a valid PNG, JPEG, or WebP image."
            )

        orig_h, orig_w = bgr.shape[:2]
        if orig_h < 16 or orig_w < 16:
            raise ImageValidationError(f"Image dimensions ({orig_w}x{orig_h}) are too small (min 16x16).")
        if orig_h > HARDWARE_CONFIG.hard_dimension_limit or orig_w > HARDWARE_CONFIG.hard_dimension_limit:
            raise ImageValidationError(
                f"Image dimensions ({orig_w}x{orig_h}) exceed hard safety limit of "
                f"{HARDWARE_CONFIG.hard_dimension_limit}px."
            )

        was_downscaled = False
        max_dim = max(orig_h, orig_w)
        if auto_resize and max_dim > HARDWARE_CONFIG.max_image_dimension:
            scale = HARDWARE_CONFIG.max_image_dimension / float(max_dim)
            new_w = max(16, int(round(orig_w * scale)))
            new_h = max(16, int(round(orig_h * scale)))
            bgr = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
            was_downscaled = True

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        del bgr, np_arr

        regions, seg_mask, perception_meta = PERCEPTION_ENGINE.analyze_image(rgb)
        session = SECURITY_ENGINE.create_session(
            filename=filename or "uploaded_image.png",
            original_sha256=input_sha256,
            original_rgb=rgb,
            was_downscaled=was_downscaled,
            original_dimensions=(orig_w, orig_h),
            regions=regions,
            seg_mask=seg_mask,
            perception_meta=perception_meta,
        )

        seg_overlay = cls.render_segmentation_overlay(rgb, seg_mask)

        return {
            "session_id": session.session_id,
            "filename": session.filename,
            "original_sha256": session.original_sha256,
            "original_dimensions": {"width": orig_w, "height": orig_h},
            "working_dimensions": {"width": session.working_dimensions[0], "height": session.working_dimensions[1]},
            "was_downscaled": was_downscaled,
            "regions": [r.model_dump() for r in session.regions],
            "perception_metadata": perception_meta,
            "semantic_classes": SEMANTIC_CLASSES,
            "original_preview_url": cls.rgb_to_data_url(rgb),
            "segmentation_overlay_url": cls.rgb_to_data_url(seg_overlay),
        }

    @classmethod
    def update_session_regions(
        cls,
        session: VigilSession,
        active_region_ids: List[str],
        excluded_region_ids: List[str],
        manual_regions: List[ManualRegionInput],
    ) -> List[DetectedRegion]:
        """Allows interactive human-in-the-loop region toggling and manual box creation."""
        base_regions = [r for r in session.regions if r.category != "manual"]
        merged = PRIVACY_ENGINE.merge_manual_regions(
            base_regions, manual_regions, session.original_rgb.shape[:2]
        )
        active_set = set(active_region_ids) if active_region_ids else None
        excluded_set = set(excluded_region_ids)

        for r in merged:
            if r.region_id in excluded_set:
                r.active = False
            elif active_set is not None:
                r.active = r.region_id in active_set

        session.regions = merged
        SECURITY_ENGINE.update_summary(session)
        return merged

    @classmethod
    def execute_vigil_pipeline(
        cls,
        session: VigilSession,
        config: TransformationConfig,
        run_evaluation: bool = True,
    ) -> Dict[str, Any]:
        """Executes the primary VIGIL transformation, security sanitisation, evaluation, and audit."""
        t0 = time.perf_counter()

        # 1. Merge any manual regions supplied in config
        if config.manual_regions:
            base_non_manual = [r for r in session.regions if r.category != "manual"]
            working_regions = PRIVACY_ENGINE.merge_manual_regions(
                base_non_manual, config.manual_regions, session.original_rgb.shape[:2]
            )
        else:
            working_regions = [r.model_copy(deep=True) for r in session.regions]

        # 2. Build protection mask with fixed exclusion logic
        seg_mask = (
            session.seg_mask
            if session.seg_mask is not None
            else np.zeros(session.original_rgb.shape[:2], dtype=np.uint8)
        )
        protection_mask, resolved_regions = PRIVACY_ENGINE.build_protection_mask(
            image_shape=session.original_rgb.shape[:2],
            regions=working_regions,
            seg_mask=seg_mask,
            config=config,
        )
        session.regions = resolved_regions

        # 3. Apply VIGIL Privacy Transformation
        transformed_rgb, transform_meta = PRIVACY_ENGINE.apply_transformation(
            rgb_image=session.original_rgb,
            protection_mask=protection_mask,
            resolved_regions=resolved_regions,
            config=config,
        )
        # Pop the numpy array out so the rest of the meta dict is JSON-safe.
        effective_target_mask = transform_meta.pop("effective_target_mask")

        # 4. Security Engine: Encode sanitized PNG & verify binary chunks
        sanitized_png_bytes = SECURITY_ENGINE.encode_and_sanitize_png(transformed_rgb)
        security_audit = SECURITY_ENGINE.verify_png_bytes(
            sanitized_png_bytes, input_sha256=session.original_sha256
        )

        # 5. Evaluation Engine: SSIM/PSNR, controlled transforms, detector retention
        evaluation_report = None
        if run_evaluation:
            evaluation_report = EVALUATION_ENGINE.evaluate(
                original_rgb=session.original_rgb,
                transformed_rgb=transformed_rgb,
                target_mask=effective_target_mask,
                resolved_regions=resolved_regions,
                config=config,
            )

        # 6. Audit Engine
        audit_report = AUDIT_ENGINE.generate_audit_report(
            session_id=session.session_id,
            original_rgb=session.original_rgb,
            transformed_rgb=transformed_rgb,
            effective_target_mask=effective_target_mask,
            resolved_regions=resolved_regions,
            config=config,
            security_audit=security_audit,
            evaluation_report=evaluation_report,
        )

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        # Store latest artifacts on session
        session.transformed_rgb = transformed_rgb
        session.protection_mask = effective_target_mask.astype(np.uint8)
        session.sanitized_png_bytes = sanitized_png_bytes
        session.last_config = config
        session.last_evaluation = evaluation_report
        session.last_audit = audit_report
        session.transformation_history.append(
            {
                "step": len(session.transformation_history) + 1,
                "timestamp_utc": audit_report.timestamp_utc,
                "method": config.method,
                "policy_id": config.policy_id,
                "random_seed": config.random_seed,
                "active_regions": audit_report.active_protected_regions,
                "target_pixel_ratio": audit_report.target_mask_pixel_ratio,
                "full_image_ssim": evaluation_report.full_image_ssim if evaluation_report else None,
                "overall_audit_status": audit_report.overall_audit_status,
                "processing_time_ms": elapsed_ms,
            }
        )
        SECURITY_ENGINE.update_summary(session)

        diff_heatmap = cls.render_difference_heatmap(session.original_rgb, transformed_rgb)
        mask_vis = np.zeros_like(session.original_rgb)
        mask_vis[effective_target_mask > 0] = (56, 189, 248)
        mask_blend = cv2.addWeighted(session.original_rgb, 0.55, mask_vis, 0.45, 0)

        gc.collect()

        return {
            "session_id": session.session_id,
            "processing_time_ms": elapsed_ms,
            "regions": [r.model_dump() for r in resolved_regions],
            "transformation_metadata": transform_meta,
            "transformation_history": session.transformation_history,
            "transformed_png_url": cls.png_bytes_to_data_url(sanitized_png_bytes),
            "protection_mask_url": cls.rgb_to_data_url(mask_blend),
            "difference_heatmap_url": cls.rgb_to_data_url(diff_heatmap),
            "evaluation_report": evaluation_report.model_dump() if evaluation_report else None,
            "audit_report": audit_report.model_dump(),
        }

    @staticmethod
    def build_export_zip(session: VigilSession) -> bytes:
        """Packages sanitized PNG, audit JSON, evaluation JSON, and history into a reproducible ZIP."""
        if session.sanitized_png_bytes is None or session.last_audit is None:
            raise ValueError("No VIGIL transformation has been executed for this session yet.")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("vigil_transformed.png", session.sanitized_png_bytes)
            zf.writestr(
                "vigil_audit_report.json",
                json.dumps(session.last_audit.model_dump(), indent=2, default=str),
            )
            if session.last_evaluation is not None:
                zf.writestr(
                    "vigil_evaluation_report.json",
                    json.dumps(session.last_evaluation.model_dump(), indent=2, default=str),
                )
            zf.writestr(
                "vigil_integrity_manifest.json",
                json.dumps(session.last_audit.integrity_manifest, indent=2, default=str),
            )
            zf.writestr(
                "vigil_transformation_history.json",
                json.dumps(session.transformation_history, indent=2, default=str),
            )
        return buf.getvalue()

    @staticmethod
    def get_system_overview() -> Dict[str, Any]:
        """Returns system status, hardware limits, model state, policies, and session summaries."""
        mem_mb = None
        try:
            import psutil

            process = psutil.Process()
            mem_mb = round(process.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            mem_mb = None

        return {
            "application": "VIGIL — Visual Integrity & Generative Interference Lab",
            "version": "2.0.0",
            "hardware_profile": {
                "target_cpu": "AMD Athlon 3000G (CPU-First Execution)",
                "cpu_threads_cap": HARDWARE_CONFIG.cpu_threads,
                "max_image_dimension": HARDWARE_CONFIG.max_image_dimension,
                "max_upload_mb": HARDWARE_CONFIG.max_upload_bytes // (1024 * 1024),
                "process_rss_mb": mem_mb,
            },
            "model_status": MODEL_MANAGER.get_status(),
            "policies": {k: vars(v) for k, v in PROTECTION_POLICIES.items()},
            "semantic_classes": SEMANTIC_CLASSES,
            "sessions": SECURITY_ENGINE.get_overview_stats(),
        }


VIGIL_CORE = VigilCore()
