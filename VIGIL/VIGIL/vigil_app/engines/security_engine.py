# vigil_app/engines/security_engine.py
"""
VIGIL Security Engine
Provides binary PNG metadata sanitisation, chunk-level CRC32 verification,
thread-safe ephemeral session isolation, and explicit memory cleanup.
"""

from __future__ import annotations

import gc
import hashlib
import struct
import threading
import time
import uuid
import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from vigil_app.config import HARDWARE_CONFIG
from vigil_app.schemas import (
    AuditReport,
    DetectedRegion,
    EvaluationReport,
    PngSecurityAudit,
    TransformationConfig,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ALLOWED_PNG_CHUNKS = {"IHDR", "IDAT", "IEND"}
FORBIDDEN_METADATA_CHUNKS = {"eXIf", "tEXt", "zTXt", "iTXt", "tIME", "iCCP", "pHYs"}


@dataclass
class VigilSession:
    session_id: str
    filename: str
    created_at: float
    last_accessed: float
    original_sha256: str
    original_rgb: np.ndarray
    was_downscaled: bool
    original_dimensions: Tuple[int, int]
    working_dimensions: Tuple[int, int]
    regions: List[DetectedRegion] = field(default_factory=list)
    seg_mask: Optional[np.ndarray] = None
    perception_meta: Dict[str, Any] = field(default_factory=dict)
    transformed_rgb: Optional[np.ndarray] = None
    protection_mask: Optional[np.ndarray] = None
    sanitized_png_bytes: Optional[bytes] = None
    last_config: Optional[TransformationConfig] = None
    last_evaluation: Optional[EvaluationReport] = None
    last_audit: Optional[AuditReport] = None
    transformation_history: List[Dict[str, Any]] = field(default_factory=list)

    def clear_buffers(self) -> None:
        """Explicitly releases large pixel arrays to keep RAM usage low on 8 GB systems."""
        self.original_rgb = np.empty((0, 0, 3), dtype=np.uint8)
        self.seg_mask = None
        self.transformed_rgb = None
        self.protection_mask = None
        self.sanitized_png_bytes = None


class SecurityEngine:
    """Handles PNG binary sanitisation, integrity verification, and isolated session storage."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: Dict[str, VigilSession] = {}
        self._recent_session_summaries: List[Dict[str, Any]] = []

    @staticmethod
    def encode_and_sanitize_png(rgb_image: np.ndarray) -> bytes:
        """Reconstructs a fresh contiguous pixel buffer, encodes to PNG, strips ancillary chunks."""
        fresh_rgb = np.array(rgb_image, dtype=np.uint8, copy=True, order="C")
        bgr = cv2.cvtColor(fresh_rgb, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".png", bgr, [int(cv2.IMWRITE_PNG_COMPRESSION), 6])
        if not ok:
            raise RuntimeError("Failed to encode image buffer to PNG.")

        raw_bytes = buf.tobytes()
        if not raw_bytes.startswith(PNG_SIGNATURE):
            raise RuntimeError("Encoded PNG buffer is missing the standard 8-byte PNG signature.")

        clean_parts: List[bytes] = [PNG_SIGNATURE]
        offset = 8
        total_len = len(raw_bytes)

        while offset + 8 <= total_len:
            length = struct.unpack(">I", raw_bytes[offset : offset + 4])[0]
            chunk_type_bytes = raw_bytes[offset + 4 : offset + 8]
            chunk_type = chunk_type_bytes.decode("ascii", errors="replace")
            chunk_end = offset + 8 + length + 4
            if chunk_end > total_len:
                break

            chunk_data = raw_bytes[offset + 8 : offset + 8 + length]
            if chunk_type in ALLOWED_PNG_CHUNKS:
                recomputed_crc = zlib.crc32(chunk_type_bytes + chunk_data) & 0xFFFFFFFF
                clean_parts.append(struct.pack(">I", length))
                clean_parts.append(chunk_type_bytes)
                clean_parts.append(chunk_data)
                clean_parts.append(struct.pack(">I", recomputed_crc))

            offset = chunk_end
            if chunk_type == "IEND":
                break

        return b"".join(clean_parts)

    @staticmethod
    def verify_png_bytes(png_bytes: bytes, input_sha256: str = "") -> PngSecurityAudit:
        """Parses a binary PNG stream, inspects every chunk header, validates CRC32 checksums."""
        output_sha256 = hashlib.sha256(png_bytes).hexdigest()
        if len(png_bytes) < 8 or not png_bytes.startswith(PNG_SIGNATURE):
            return PngSecurityAudit(
                is_clean_png=False,
                chunks_present=[],
                forbidden_metadata_chunks_found=["INVALID_PNG_SIGNATURE"],
                all_crc32_valid=False,
                input_sha256=input_sha256,
                output_sha256=output_sha256,
                byte_size=len(png_bytes),
            )

        chunks_present: List[str] = []
        forbidden_found: List[str] = []
        all_crc_ok = True

        offset = 8
        total_len = len(png_bytes)
        while offset + 8 <= total_len:
            length = struct.unpack(">I", png_bytes[offset : offset + 4])[0]
            chunk_type_bytes = png_bytes[offset + 4 : offset + 8]
            chunk_type = chunk_type_bytes.decode("ascii", errors="replace")
            data_end = offset + 8 + length
            crc_end = data_end + 4

            if crc_end > total_len:
                all_crc_ok = False
                break

            chunk_data = png_bytes[offset + 8 : data_end]
            stored_crc = struct.unpack(">I", png_bytes[data_end:crc_end])[0]
            computed_crc = zlib.crc32(chunk_type_bytes + chunk_data) & 0xFFFFFFFF

            if stored_crc != computed_crc:
                all_crc_ok = False

            chunks_present.append(chunk_type)
            if chunk_type not in ALLOWED_PNG_CHUNKS or chunk_type in FORBIDDEN_METADATA_CHUNKS:
                forbidden_found.append(chunk_type)

            offset = crc_end
            if chunk_type == "IEND":
                break

        has_required = ("IHDR" in chunks_present) and ("IDAT" in chunks_present) and ("IEND" in chunks_present)
        is_clean = bool(has_required and len(forbidden_found) == 0 and all_crc_ok)

        return PngSecurityAudit(
            is_clean_png=is_clean,
            chunks_present=chunks_present,
            forbidden_metadata_chunks_found=forbidden_found,
            all_crc32_valid=all_crc_ok,
            input_sha256=input_sha256,
            output_sha256=output_sha256,
            byte_size=len(png_bytes),
        )

    def _prune_unlocked(self) -> None:
        now = time.time()
        expired_ids = [
            sid
            for sid, sess in self._sessions.items()
            if (now - sess.last_accessed) > HARDWARE_CONFIG.session_ttl_seconds
        ]
        for sid in expired_ids:
            sess = self._sessions.pop(sid, None)
            if sess is not None:
                sess.clear_buffers()

        while len(self._sessions) > HARDWARE_CONFIG.max_active_sessions:
            oldest_sid = min(self._sessions.keys(), key=lambda k: self._sessions[k].last_accessed)
            old_sess = self._sessions.pop(oldest_sid, None)
            if old_sess is not None:
                old_sess.clear_buffers()

        if expired_ids:
            gc.collect()

    def create_session(
        self,
        filename: str,
        original_sha256: str,
        original_rgb: np.ndarray,
        was_downscaled: bool,
        original_dimensions: Tuple[int, int],
        regions: List[DetectedRegion],
        seg_mask: np.ndarray,
        perception_meta: Dict[str, Any],
    ) -> VigilSession:
        with self._lock:
            self._prune_unlocked()
            session_id = f"vigil_{uuid.uuid4().hex[:12]}"
            now = time.time()
            h, w = original_rgb.shape[:2]
            session = VigilSession(
                session_id=session_id,
                filename=filename,
                created_at=now,
                last_accessed=now,
                original_sha256=original_sha256,
                original_rgb=original_rgb,
                was_downscaled=was_downscaled,
                original_dimensions=original_dimensions,
                working_dimensions=(w, h),
                regions=regions,
                seg_mask=seg_mask,
                perception_meta=perception_meta,
            )
            self._sessions[session_id] = session
            self._record_summary_unlocked(session)
            self._prune_unlocked()
            return session

    def get_session(self, session_id: str) -> Optional[VigilSession]:
        with self._lock:
            self._prune_unlocked()
            sess = self._sessions.get(session_id)
            if sess is not None:
                sess.last_accessed = time.time()
            return sess

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            sess = self._sessions.pop(session_id, None)
            if sess is not None:
                sess.clear_buffers()
                gc.collect()
                return True
            return False

    def update_summary(self, session: VigilSession) -> None:
        with self._lock:
            self._record_summary_unlocked(session)

    def _record_summary_unlocked(self, session: VigilSession) -> None:
        summary = {
            "session_id": session.session_id,
            "filename": session.filename,
            "created_at": session.created_at,
            "working_dimensions": f"{session.working_dimensions[0]}x{session.working_dimensions[1]}",
            "detected_regions_count": len(session.regions),
            "last_method": session.last_config.method if session.last_config else "not_executed",
            "audit_status": session.last_audit.overall_audit_status if session.last_audit else "PENDING",
            "full_image_ssim": (
                session.last_evaluation.full_image_ssim if session.last_evaluation else None
            ),
            "is_active_in_ram": session.session_id in self._sessions,
        }
        self._recent_session_summaries = [
            s for s in self._recent_session_summaries if s["session_id"] != session.session_id
        ]
        self._recent_session_summaries.insert(0, summary)
        self._recent_session_summaries = self._recent_session_summaries[:15]

    def get_overview_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._prune_unlocked()
            for sid, sess in self._sessions.items():
                self._record_summary_unlocked(sess)
            return {
                "active_sessions_in_ram": len(self._sessions),
                "max_active_sessions": HARDWARE_CONFIG.max_active_sessions,
                "session_ttl_seconds": HARDWARE_CONFIG.session_ttl_seconds,
                "recent_sessions": list(self._recent_session_summaries),
            }


SECURITY_ENGINE = SecurityEngine()
