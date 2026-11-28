# packages/vigil/schemas.py
"""
Pydantic Schemas for VIGIL API Requests, Regions, Transformations, Evaluations, and Audits.
All dictionary keys use strict snake_case to ensure safe JavaScript property access.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

RegionCategory = Literal["face", "qr_code", "text", "licence_plate", "manual"]
TransformationMethod = Literal[
    "none",
    "solid",
    "pixelate",
    "blur",
    "gaussian_noise",
    "structured_freq",
    "composite_redact_and_noise",
]


class BoundingBox(BaseModel):
    x1: int = Field(..., ge=0)
    y1: int = Field(..., ge=0)
    x2: int = Field(..., ge=0)
    y2: int = Field(..., ge=0)

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def area(self) -> int:
        return self.width * self.height


class DetectedRegion(BaseModel):
    region_id: str
    category: RegionCategory
    bbox: BoundingBox
    confidence: float = Field(..., ge=0.0, le=1.0)
    detector_source: str
    active: bool = True
    semantic_classes_present: List[str] = Field(default_factory=list)
    notes: str = ""


class ManualRegionInput(BaseModel):
    region_id: Optional[str] = None
    category: RegionCategory = "manual"
    x1: int = Field(..., ge=0)
    y1: int = Field(..., ge=0)
    x2: int = Field(..., ge=0)
    y2: int = Field(..., ge=0)
    active: bool = True


class TransformationConfig(BaseModel):
    policy_id: str = Field(default="policy_strict")
    method: TransformationMethod = Field(default="gaussian_noise")
    pixel_block_size: int = Field(default=14, ge=2, le=64)
    blur_kernel_size: int = Field(default=31, ge=3, le=99)
    solid_color_rgb: List[int] = Field(default_factory=lambda: [24, 24, 24])
    mask_dilation_px: int = Field(default=3, ge=0, le=25)
    noise_sigma: float = Field(default=18.0, ge=0.0, le=85.0)
    freq_strength: float = Field(default=12.0, ge=0.0, le=50.0)
    apply_noise_to: Literal["selected_regions", "unredacted_background", "full_image"] = "selected_regions"
    random_seed: int = Field(default=42, ge=0, le=2_147_483_647)
    active_region_ids: Optional[List[str]] = None
    excluded_region_ids: List[str] = Field(default_factory=list)
    active_semantic_classes: List[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6])
    manual_regions: List[ManualRegionInput] = Field(default_factory=list)
    strip_metadata: bool = True
    apply_visible_watermark: bool = False


class TransformRequest(BaseModel):
    session_id: str
    config: TransformationConfig
    run_evaluation: bool = True


class ControlledTransformMetric(BaseModel):
    transform_key: str
    transform_name: str
    ssim_vs_transformed: float
    psnr_vs_transformed_db: float
    perturbation_retention_ratio: float
    post_transform_face_detections: int
    interpretation: str


class DetectorRetentionResult(BaseModel):
    category: str
    detector_name: str
    count_before: int
    count_after: int
    retained_ratio: float
    matched_regions_after: int
    status_note: str


class EvaluationReport(BaseModel):
    experiment_id: str
    reproducibility_hash: str
    random_seed: int
    full_image_ssim: float
    full_image_psnr_db: float
    unprotected_background_ssim: float
    unprotected_background_psnr_db: float
    protected_region_ssim: float
    protected_region_psnr_db: float
    protected_region_mean_l1_diff: float
    detector_retention: List[DetectorRetentionResult]
    controlled_transforms: List[ControlledTransformMetric]
    test_registry: Dict[str, Dict[str, str]]
    scientific_disclaimers: List[str]


class PngSecurityAudit(BaseModel):
    is_clean_png: bool
    chunks_present: List[str]
    forbidden_metadata_chunks_found: List[str]
    all_crc32_valid: bool
    input_sha256: str
    output_sha256: str
    byte_size: int


class AuditReport(BaseModel):
    audit_id: str
    timestamp_utc: str
    session_id: str
    system_mode: Literal["NEURAL_WEIGHTS_ACTIVE", "FALLBACK_HEURISTIC_MODE"]
    model_info: Dict[str, Any]
    transformation_config: TransformationConfig
    total_detected_regions: int
    active_protected_regions: int
    excluded_regions_count: int
    target_mask_pixel_ratio: float
    modified_pixels_within_target_ratio: float
    unintended_background_modification_ratio: float
    security_verification: PngSecurityAudit
    evaluation_summary: Optional[EvaluationReport] = None
    integrity_manifest: Dict[str, Any]
    checks: Dict[str, str]
    overall_audit_status: Literal["PASS", "WARN", "FAIL"]
    status_reasons: List[str]
    evaluation_limitations: List[str]
