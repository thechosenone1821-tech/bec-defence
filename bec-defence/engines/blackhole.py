"""Information-scrambling (ransomware-like) file-write monitor.

Day-1 redesign relative to the original prototype:

* File extensions are **context**, not a blanket bypass. A ``.zip`` is no
  longer trusted by default; its magic-byte signature, entropy delta versus
  the previous write to the same path, modification burst across sibling
  files, and canary status are combined into a single score.

* Writes below ``min_chunk_bytes`` are no longer skipped. Their entropy is
  down-weighted (small-chunk entropy is noisy) and aggregated with other
  evidence instead of judged on a single chunk.

* Per-path state (last entropy, last signature, last write tick) is tracked
  so the monitor can detect "this path's entropy jumped from 4.5 to 7.9" --
  the single most reliable ransomware signal available without process
  telemetry.

* Canary matches still produce a critical alert and short-circuit further
  scoring, because a configured canary being touched is unambiguous.

The returned object is a :class:`FileWriteAssessment` (with a ``to_dict``
helper for callers that prefer dicts). All numeric fields are unrounded
internally; round at display time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Any

import numpy as np


# Common file signatures we can recognise from the first few bytes. Sourced
# from public file-format references; intentionally short to keep the check
# cheap. A signature of "UNKNOWN" means no known header matched.
FILE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"PK\x03\x04", "zip"),
    (b"\x1f\x8b", "gzip"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"%PDF-", "pdf"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"\x00\x00\x01\xba", "mpeg"),  # MPEG-PS; coarse
    (b"ftyp", "mp4-ish"),  # appears at offset 4 in MP4 family; see _detect_signature
]

# Extensions we record as "naturally high-entropy" context, so a high entropy
# on a .zip is less surprising than on a .txt. Used as a prior only.
HIGH_ENTROPY_EXTENSIONS: frozenset[str] = frozenset(
    {".zip", ".gz", ".jpg", ".jpeg", ".png", ".mp4", ".7z", ".pdf", ".bz2", ".xz"}
)


@dataclass
class PathState:
    """Per-path rolling state used to compute entropy deltas and bursts."""

    last_entropy: float | None = None
    last_signature: str | None = None
    last_write_tick: int = 0
    write_count: int = 0


@dataclass
class FileWriteAssessment:
    """Structured assessment of a single file-write event.

    ``alert`` is the bottom-line boolean. ``score`` is a 0..1 aggregate of
    the individual signals; ``evidence`` lists which signals fired so a
    human or downstream correlation layer can reason about it.
    """

    alert: bool
    severity: str | None
    reason: str
    file: str
    score: float
    entropy: float | None
    entropy_delta: float | None
    signature: str | None
    signature_changed: bool
    burst_score: float
    evidence: list[str] = field(default_factory=list)
    recommended_action: str = "log"

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert": self.alert,
            "severity": self.severity,
            "reason": self.reason,
            "file": self.file,
            "score": round(float(self.score), 3),
            "entropy": None if self.entropy is None else round(float(self.entropy), 3),
            "entropy_delta": (
                None if self.entropy_delta is None else round(float(self.entropy_delta), 3)
            ),
            "signature": self.signature,
            "signature_changed": self.signature_changed,
            "burst_score": round(float(self.burst_score), 3),
            "evidence": list(self.evidence),
            "recommended_action": self.recommended_action,
        }


@dataclass
class _BurstWindow:
    """Rolling count of distinct paths written in the last ``window_seconds``."""

    timestamps: list[float] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)

    def add(self, path: str, ts: float, window_seconds: float) -> tuple[int, float]:
        self.timestamps.append(ts)
        self.paths.append(path)
        cutoff = ts - window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.pop(0)
            self.paths.pop(0)
        distinct = len(set(self.paths))
        rate = distinct / max(window_seconds, 1e-6)
        return distinct, rate


class InformationScramblingMonitor:
    """Contextual file-write monitor for ransomware-like scrambling."""

    def __init__(
        self,
        canary_patterns: tuple[str, ...] = (),
        entropy_threshold: float = 7.2,
        entropy_delta_threshold: float = 2.0,
        min_chunk_bytes: int = 512,
        burst_window_seconds: float = 10.0,
        burst_distinct_threshold: int = 20,
        alarm_score_threshold: float = 0.6,
        clock=time.monotonic,
    ):
        if entropy_threshold <= 0 or entropy_threshold > 8.0:
            raise ValueError("entropy_threshold must be in (0, 8.0]")
        if entropy_delta_threshold < 0:
            raise ValueError("entropy_delta_threshold must be >= 0")
        if min_chunk_bytes < 1:
            raise ValueError("min_chunk_bytes must be >= 1")
        if burst_window_seconds <= 0:
            raise ValueError("burst_window_seconds must be > 0")
        if burst_distinct_threshold < 1:
            raise ValueError("burst_distinct_threshold must be >= 1")
        if not 0.0 < alarm_score_threshold <= 1.0:
            raise ValueError("alarm_score_threshold must be in (0, 1]")

        self.canary_patterns = tuple(canary_patterns)
        self.entropy_threshold = float(entropy_threshold)
        self.entropy_delta_threshold = float(entropy_delta_threshold)
        self.min_chunk_bytes = int(min_chunk_bytes)
        self.burst_window_seconds = float(burst_window_seconds)
        self.burst_distinct_threshold = int(burst_distinct_threshold)
        self.alarm_score_threshold = float(alarm_score_threshold)
        self._clock = clock

        self.path_state: dict[str, PathState] = {}
        self._burst = _BurstWindow()
        self._tick = 0

    # -- pure helpers ------------------------------------------------------- #
    @staticmethod
    def shannon_entropy(data: bytes) -> float:
        if len(data) < 2:
            return 0.0
        counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
        p = counts[counts > 0] / len(data)
        return float(-(p * np.log2(p)).sum())

    @staticmethod
    def _detect_signature(chunk: bytes) -> str:
        if not chunk:
            return "EMPTY"
        for magic, name in FILE_SIGNATURES:
            if name == "mp4-ish":
                if len(chunk) >= 12 and chunk[4:8] == b"ftyp":
                    return "mp4"
                continue
            if chunk.startswith(magic):
                return name
        # Heuristic: mostly printable ASCII -> "text-like"
        sample = chunk[:64]
        printable = sum(1 for b in sample if 9 <= b <= 13 or 32 <= b <= 126)
        if printable / max(len(sample), 1) > 0.85:
            return "text"
        return "UNKNOWN"

    @staticmethod
    def _extension_of(path: str) -> str:
        dot = path.rfind(".")
        slash = max(path.rfind("/"), path.rfind("\\"))
        if dot > slash:
            return path[dot:].lower()
        return ""

    # -- public API --------------------------------------------------------- #
    def reset(self) -> None:
        self.path_state.clear()
        self._burst = _BurstWindow()
        self._tick = 0

    def inspect_file_write(self, file_path: str, chunk: bytes) -> FileWriteAssessment:
        """Inspect a single write event and update per-path / burst state."""
        if not isinstance(file_path, str) or not file_path:
            raise ValueError("file_path must be a non-empty string")
        if not isinstance(chunk, (bytes, bytearray)):
            raise ValueError("chunk must be bytes")
        chunk = bytes(chunk)

        self._tick += 1
        ts = float(self._clock())

        # 1. Canary short-circuits -- a configured canary being touched is
        # unambiguous and we do not need further scoring.
        for pat in self.canary_patterns:
            if fnmatch(file_path, pat):
                return FileWriteAssessment(
                    alert=True,
                    severity="critical",
                    reason="CANARY_TOUCHED",
                    file=file_path,
                    score=1.0,
                    entropy=None,
                    entropy_delta=None,
                    signature=None,
                    signature_changed=False,
                    burst_score=0.0,
                    evidence=[f"matched canary pattern {pat!r}"],
                    recommended_action="quarantine",
                )

        # 2. Per-path state and signature.
        state = self.path_state.get(file_path)
        if state is None:
            state = PathState()
            self.path_state[file_path] = state

        H_raw = self.shannon_entropy(chunk)
        # Small chunks: entropy is noisy, so down-weight it linearly toward
        # zero below min_chunk_bytes. Do NOT skip inspection.
        if len(chunk) < self.min_chunk_bytes:
            weight = len(chunk) / float(self.min_chunk_bytes)
            H = H_raw * weight
            small_chunk = True
        else:
            H = H_raw
            small_chunk = False

        sig = self._detect_signature(chunk)
        prev_entropy = state.last_entropy
        prev_sig = state.last_signature
        entropy_delta = (H - prev_entropy) if prev_entropy is not None else None
        signature_changed = prev_sig is not None and sig != prev_sig

        # 3. Burst across sibling-ish paths in the rolling window.
        distinct, rate = self._burst.add(file_path, ts, self.burst_window_seconds)
        burst_score = min(distinct / float(self.burst_distinct_threshold), 1.0)

        # 4. Extension context: high-entropy extensions get a small prior
        # discount on the absolute-entropy signal, but it never zeroes out.
        ext = self._extension_of(file_path)
        ext_is_high_entropy = ext in HIGH_ENTROPY_EXTENSIONS

        # 5. Score combination. Each signal contributes a 0..1 sub-score;
        # the aggregate is a weighted sum. Weights sum to 1.0.
        evidence: list[str] = []

        s_entropy = 0.0
        if H > self.entropy_threshold:
            raw = min((H - self.entropy_threshold) / (8.0 - self.entropy_threshold), 1.0)
            if ext_is_high_entropy:
                raw *= 0.5
                evidence.append(
                    f"entropy {H:.2f} exceeds threshold but extension {ext or 'none'} "
                    f"is high-entropy context (discounted)"
                )
            else:
                evidence.append(f"entropy {H:.2f} exceeds threshold {self.entropy_threshold}")
            s_entropy = raw

        s_delta = 0.0
        if entropy_delta is not None and entropy_delta > self.entropy_delta_threshold:
            s_delta = min(entropy_delta / 4.0, 1.0)
            evidence.append(
                f"entropy delta {entropy_delta:+.2f} exceeds "
                f"{self.entropy_delta_threshold} versus previous write"
            )

        s_sig = 0.0
        if signature_changed:
            # A signature change is suspicious only when the new signature
            # is UNKNOWN or differs from what the extension claims.
            if sig in {"UNKNOWN"} or (
                ext in {".zip", ".gz", ".jpg", ".jpeg", ".png", ".7z", ".pdf"}
                and sig not in {ext.lstrip("."), "jpeg" if ext == ".jpg" else ext.lstrip(".")}
            ):
                s_sig = 0.6
                evidence.append(
                    f"signature changed {prev_sig!r} -> {sig!r} "
                    f"(extension {ext or 'none'} no longer matches header)"
                )
            else:
                evidence.append(
                    f"signature changed {prev_sig!r} -> {sig!r} but matches extension"
                )

        s_burst = burst_score
        if s_burst > 0:
            evidence.append(
                f"{distinct} distinct files written in last "
                f"{self.burst_window_seconds:.0f}s (burst_score {s_burst:.2f})"
            )

        if small_chunk:
            evidence.append(
                f"chunk {len(chunk)}B below {self.min_chunk_bytes}B; entropy down-weighted"
            )

        # Weighted aggregate. Absolute entropy is weighted lower because on
        # its own it is the weakest signal; delta + burst + signature are
        # the behavioural signals that matter.
        weights = {"entropy": 0.20, "delta": 0.30, "sig": 0.20, "burst": 0.30}
        score = (
            weights["entropy"] * s_entropy
            + weights["delta"] * s_delta
            + weights["sig"] * s_sig
            + weights["burst"] * s_burst
        )

        alert = score >= self.alarm_score_threshold
        # Severity ladders with score and which signals fired.
        if alert:
            if s_delta > 0 and s_burst > 0:
                severity = "critical"
                reason = "BEHAVIOURAL_SCRAMBLING"
                recommended_action = "quarantine"
            elif s_burst > 0 or s_delta > 0:
                severity = "high"
                reason = "HIGH_ENTROPY_SCRAMBLING"
                recommended_action = "quarantine"
            else:
                severity = "medium"
                reason = "ENTROPY_ANOMALY"
                recommended_action = "log"
        else:
            severity = None
            reason = "OK" if not evidence else "WEAK_SIGNALS"
            recommended_action = "log"

        # 6. Update per-path state for next time.
        state.last_entropy = H
        state.last_signature = sig
        state.last_write_tick = self._tick
        state.write_count += 1

        return FileWriteAssessment(
            alert=alert,
            severity=severity,
            reason=reason,
            file=file_path,
            score=score,
            entropy=H,
            entropy_delta=entropy_delta,
            signature=sig,
            signature_changed=signature_changed,
            burst_score=burst_score,
            evidence=evidence,
            recommended_action=recommended_action,
        )

    def modification_burst(self) -> dict[str, Any]:
        """Snapshot of the current rolling burst window (for diagnostics)."""
        ts = float(self._clock())
        # Trim before reporting so the window reflects "now".
        cutoff = ts - self.burst_window_seconds
        while self._burst.timestamps and self._burst.timestamps[0] < cutoff:
            self._burst.timestamps.pop(0)
            self._burst.paths.pop(0)
        distinct = len(set(self._burst.paths))
        return {
            "distinct_paths": distinct,
            "rate_per_second": distinct / max(self.burst_window_seconds, 1e-6),
            "threshold": self.burst_distinct_threshold,
            "window_seconds": self.burst_window_seconds,
        }
