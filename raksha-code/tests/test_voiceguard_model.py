import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citizen.voiceguard.model import OnnxAntiSpoofModel
from citizen.voiceguard.voiceguard import score_voice

class _Input:
    name = "waveform"
    shape = [1, 32000]

class _Session:
    def __init__(self, output):
        self.output = output
        self.last_feed = None
    def get_inputs(self):
        return [_Input()]
    def run(self, _names, feed):
        self.last_feed = feed
        return [np.asarray(self.output, dtype=np.float32)]

def test_onnx_adapter_passes_16khz_window_as_batch():
    session = _Session([0.92])
    model = OnnxAntiSpoofModel(session=session)
    assert model.predict_spoof_probability(np.zeros(32000, dtype=np.float32)) == pytest.approx(0.92)
    assert session.last_feed["waveform"].shape == (1, 32000)

def test_two_logits_are_interpreted_as_bonafide_then_spoof():
    model = OnnxAntiSpoofModel(session=_Session([0.0, 3.0]))
    assert model.predict_spoof_probability(np.zeros(32000, dtype=np.float32)) > 0.9

def test_scalar_logit_is_sigmoid_normalized():
    model = OnnxAntiSpoofModel(session=_Session([2.0]))
    assert model.predict_spoof_probability(np.zeros(32000, dtype=np.float32)) == pytest.approx(0.8808, abs=1e-3)

def test_model_rejects_wrong_export_shape():
    class BadSession(_Session):
        def get_inputs(self):
            item = _Input()
            item.shape = [1, 1, 32000]
            return [item]
    with pytest.raises(ValueError):
        OnnxAntiSpoofModel(session=BadSession([0.5]))

def test_model_requires_exact_two_second_waveform():
    model = OnnxAntiSpoofModel(session=_Session([0.5]))
    with pytest.raises(ValueError):
        model.predict_spoof_probability(np.zeros(16000, dtype=np.float32))

def test_score_uses_model_probability_bands():
    audio = (0.4 * np.sin(2 * np.pi * 220 * np.arange(32000) / 16000)).astype(np.float32)
    suspicious = score_voice(audio, model=OnnxAntiSpoofModel(session=_Session([0.95])))
    likely = score_voice(audio, model=OnnxAntiSpoofModel(session=_Session([0.05])))
    uncertain = score_voice(audio, model=OnnxAntiSpoofModel(session=_Session([0.5])))
    assert suspicious["verdict"] == "SUSPICIOUS"
    assert likely["verdict"] == "LIKELY_GENUINE"
    assert uncertain["verdict"] == "INCONCLUSIVE"

def test_model_runtime_failure_fails_closed():
    class BrokenModel:
        def predict_spoof_probability(self, _audio):
            raise RuntimeError("broken inference")
    result = score_voice(np.ones(32000, dtype=np.float32) * 0.2, model=BrokenModel())
    assert result["verdict"] == "INCONCLUSIVE"
    assert result["engine"] == "model_error_fail_closed"

def test_model_probability_outside_range_fails_closed():
    class BadModel:
        def predict_spoof_probability(self, _audio):
            return 1.4
    result = score_voice(np.ones(32000, dtype=np.float32) * 0.2, model=BadModel())
    assert result["verdict"] == "INCONCLUSIVE"
