# packages/vigil/config.py
"""
VIGIL Configuration & Hardware Constraints
Target System: AMD Athlon 3000G (2 physical cores / 4 threads, 8 GB DDR4 RAM, CPU-only)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

BASE_DIR: Path = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHTS_CANDIDATES: List[Path] = [
    BASE_DIR / "packages/vigil/weights/cloakpixel_privacynet_384.torchscript.pt",
    BASE_DIR / "packages/vigil/weights/best_privacynet.pt",
]


@dataclass(frozen=True)
class HardwareConfig:
    """CPU & memory guardrails tuned for dual-core / 8 GB RAM systems."""
    cpu_threads: int = min(2, max(1, os.cpu_count() or 1))
    max_upload_bytes: int = 12 * 1024 * 1024
    max_image_dimension: int = 1600
    hard_dimension_limit: int = 4096
    model_input_size: int = 384
    max_active_sessions: int = 3
    session_ttl_seconds: int = 300


@dataclass(frozen=True)
class ProtectionPolicy:
    policy_id: str
    name: str
    description: str
    target_categories: List[str]
    target_semantic_classes: List[int]
    default_method: str


SEMANTIC_CLASSES: Dict[int, str] = {
    0: "background",
    1: "facial_skin",
    2: "eyes_and_eyebrows",
    3: "nose",
    4: "mouth_and_lips",
    5: "ears",
    6: "hair_and_head",
}

PROTECTION_POLICIES: Dict[str, ProtectionPolicy] = {
    "policy_strict": ProtectionPolicy(
        policy_id="policy_strict",
        name="Strict Sensitive Region Protection",
        description="Selects all detected faces, QR codes, text regions, and licence plates.",
        target_categories=["face", "qr_code", "text", "licence_plate", "manual"],
        target_semantic_classes=[1, 2, 3, 4, 5, 6],
        default_method="pixelate",
    ),
    "policy_biometric_only": ProtectionPolicy(
        policy_id="policy_biometric_only",
        name="Facial Features & Identifiers Only",
        description="Selects primary facial features (skin, eyes, nose, mouth) and QR codes; excludes hair.",
        target_categories=["face", "qr_code", "manual"],
        target_semantic_classes=[1, 2, 3, 4],
        default_method="gaussian_noise",
    ),
    "policy_document_text": ProtectionPolicy(
        policy_id="policy_document_text",
        name="Text, Plates & Barcodes Only",
        description="Selects text regions, licence plates, and QR codes while leaving faces unmodified.",
        target_categories=["qr_code", "text", "licence_plate", "manual"],
        target_semantic_classes=[],
        default_method="solid",
    ),
    "policy_manual": ProtectionPolicy(
        policy_id="policy_manual",
        name="Manual Selection Only",
        description="Disables automatic selection; only applies transformations to manually selected regions.",
        target_categories=["manual"],
        target_semantic_classes=[],
        default_method="blur",
    ),
}

EVALUATION_TEST_REGISTRY: Dict[str, Dict[str, str]] = {
    "visual_similarity_ssim_psnr": {
        "name": "Full-Image & Background SSIM / PSNR",
        "status": "AVAILABLE",
        "scope": "Measures structural and peak signal-to-noise similarity for human viewing quality.",
        "limitation": "High or low SSIM/PSNR measures visual fidelity only; it does not measure identity protection.",
    },
    "local_detector_retention": {
        "name": "Pre/Post Local Detector Retention Test",
        "status": "AVAILABLE",
        "scope": "Re-runs the configured OpenCV/heuristic face, QR, text, and plate detectors on the transformed image.",
        "limitation": "Measures detection suppression against the specific local detector only. Failure to detect here does not guarantee resistance against modern deep-learning facial recognition or OCR models.",
    },
    "controlled_transform_stability": {
        "name": "Controlled Perturbation Survival (JPEG Q=75, Resize 0.5x, Blur 3x3)",
        "status": "AVAILABLE",
        "scope": "Measures how much of the applied pixel transformation survives standard lossy re-encoding and resizing.",
        "limitation": "Measures signal survival under compression/resizing only. It is NOT proof of resistance to facial recognition or deepfake generation.",
    },
    "deep_face_embedding_distance": {
        "name": "Deep Facial Recognition Embedding Distance (ArcFace / AdaFace)",
        "status": "UNAVAILABLE",
        "scope": "Measures cosine distance shift in identity embedding space.",
        "limitation": "Unavailable in the lightweight CPU build to respect the 8 GB RAM / Athlon 3000G constraint.",
    },
    "generative_inpainting_resistance": {
        "name": "Generative Diffusion Edit / Deepfake Interference Benchmark",
        "status": "UNAVAILABLE",
        "scope": "Evaluates disruption of latent diffusion inpainting models.",
        "limitation": "Requires multi-GB diffusion weights and GPU compute; marked UNAVAILABLE rather than simulated.",
    },
}

HARDWARE_CONFIG = HardwareConfig()
