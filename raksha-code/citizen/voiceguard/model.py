"""Optional local ONNX anti-spoof adapter.

The adapter supports one documented export contract: float32 [1, 32000]
mono audio at 16 kHz; output is one spoof probability or two logits ordered
[bonafide, spoof]. Model weights are not bundled with RAKSHA.
"""
from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Any, Optional
import numpy as np

_EXPECTED_SAMPLES = 32_000
_LOCK = threading.Lock()
_CACHED_PATH: Optional[str] = None
_CACHED_MODEL: Optional["OnnxAntiSpoofModel"] = None
_CACHED_ERROR: Optional[str] = None

class OnnxAntiSpoofModel:
    """CPU-capable ONNX wrapper for the VoiceGuard waveform contract."""
    def __init__(self, model_path: Optional[str] = None, session: Any = None):
        if session is None:
            if not model_path:
                raise ValueError("model_path is required")
            if not Path(model_path).is_file():
                raise FileNotFoundError("configured ONNX model file does not exist")
            try:
                import onnxruntime as ort
            except ImportError as exc:
                raise RuntimeError("onnxruntime is not installed; install requirements-voiceguard-onnx.txt") from exc
            session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        inputs = session.get_inputs()
        if len(inputs) != 1:
            raise ValueError("VoiceGuard ONNX export must expose exactly one input")
        shape = list(inputs[0].shape)
        if len(shape) != 2 or (isinstance(shape[-1], int) and shape[-1] != _EXPECTED_SAMPLES):
            raise ValueError("VoiceGuard ONNX input must have shape [1, 32000] or [batch, dynamic]")
        self._session = session
        self._input_name = inputs[0].name

    def predict_spoof_probability(self, samples: np.ndarray) -> float:
        audio = np.asarray(samples, dtype=np.float32)
        if audio.ndim != 1 or audio.size != _EXPECTED_SAMPLES:
            raise ValueError("ONNX inference requires exactly 32000 mono samples at 16 kHz")
        outputs = self._session.run(None, {self._input_name: audio.reshape(1, -1)})
        if not outputs:
            raise ValueError("ONNX model returned no outputs")
        values = np.asarray(outputs[0], dtype=np.float64).reshape(-1)
        if values.size == 1:
            value = float(values[0])
            if 0.0 <= value <= 1.0:
                return value
            if not np.isfinite(value):
                raise ValueError("ONNX model returned a non-finite value")
            return float(1.0 / (1.0 + np.exp(-np.clip(value, -60.0, 60.0))))
        if values.size == 2:
            if not np.isfinite(values).all():
                raise ValueError("ONNX model returned non-finite logits")
            shifted = values - np.max(values)
            probabilities = np.exp(shifted) / np.sum(np.exp(shifted))
            return float(probabilities[1])
        raise ValueError("ONNX output must be one spoof probability or two class logits")


def get_model() -> Optional[OnnxAntiSpoofModel]:
    """Load once from RAKSHA_VOICEGUARD_ONNX; return None on safe fallback."""
    global _CACHED_PATH, _CACHED_MODEL, _CACHED_ERROR
    configured = os.environ.get("RAKSHA_VOICEGUARD_ONNX", "").strip() or None
    with _LOCK:
        if configured == _CACHED_PATH:
            return _CACHED_MODEL
        _CACHED_PATH, _CACHED_MODEL, _CACHED_ERROR = configured, None, None
        if configured:
            try:
                _CACHED_MODEL = OnnxAntiSpoofModel(model_path=configured)
            except Exception as exc:
                _CACHED_ERROR = type(exc).__name__
        return _CACHED_MODEL


def get_model_status() -> dict[str, object]:
    """Return readiness without exposing a local filesystem path."""
    model = get_model()
    return {
        "configured": bool(os.environ.get("RAKSHA_VOICEGUARD_ONNX", "").strip()),
        "loaded": model is not None,
        "error": _CACHED_ERROR,
        "contract": "mono_float32_16khz_32000_samples_to_spoof_probability",
    }
