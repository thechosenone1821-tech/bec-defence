# engines/blackhole.py
import numpy as np
from fnmatch import fnmatch

class InformationScramblingMonitor:
    def __init__(self, canary_patterns, entropy_threshold=7.2,
                 min_chunk_bytes=512, allow_patterns=("*.zip", "*.gz", "*.jpg",
                                                      "*.png", "*.mp4", "*.7z")):
        self.canary_patterns = canary_patterns       # e.g. ("/vault/*.docx", "*.canary")
        self.entropy_threshold = entropy_threshold   # 8.0 = perfectly uniform bytes
        self.min_chunk_bytes = min_chunk_bytes       # entropy on tiny chunks is noise
        self.allow_patterns = allow_patterns         # legitimately high-entropy formats

    @staticmethod
    def shannon_entropy(data: bytes) -> float:
        if len(data) < 2:
            return 0.0
        counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
        p = counts[counts > 0] / len(data)           # vectorised; Counter is ~50x slower
        return float(-(p * np.log2(p)).sum())

    def inspect_file_write(self, file_path: str, chunk: bytes) -> dict:
        if any(fnmatch(file_path, pat) for pat in self.canary_patterns):
            return {"alert": True, "severity": "critical", "reason": "CANARY_TOUCHED",
                    "file": file_path, "entropy": None}
        if any(fnmatch(file_path, pat) for pat in self.allow_patterns):
            return {"alert": False, "reason": "ALLOWLISTED_FORMAT", "entropy": None}
        if len(chunk) < self.min_chunk_bytes:
            return {"alert": False, "reason": "CHUNK_TOO_SMALL", "entropy": None}

        H = self.shannon_entropy(chunk)
        if H > self.entropy_threshold:
            return {"alert": True, "severity": "high", "reason": "HIGH_ENTROPY_SCRAMBLING",
                    "entropy": round(H, 3), "file": file_path}
        return {"alert": False, "reason": "OK", "entropy": round(H, 3)}