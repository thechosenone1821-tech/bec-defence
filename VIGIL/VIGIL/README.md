# VIGIL 2.0 — Visual Integrity & Generative Interference Lab

**VIGIL** is a privacy-oriented image transformation and evaluation platform. It is designed to:
1. Retain high visual similarity in unmodified regions for ordinary human viewing.
2. Reduce exposure of sensitive visual information (faces, facial sub-regions, QR codes, text regions, and licence plates) via configurable transformations (seeded Gaussian noise, structured frequency interference, pixelation, Gaussian blur, and solid redaction).
3. Evaluate transformed outputs against explicitly identified local detectors and controlled image processing transformations (`jpeg_q75`, `resize_0_5x`, `gaussian_blur_3x3`).
4. Produce transparent, reproducible, machine-readable JSON audit reports and metadata-sanitized PNG exports.

---

## Actual Capabilities vs. Explicit Scientific Limitations

VIGIL enforces strict scientific and reporting integrity:
* **No Fabricated Claims**: VIGIL does **not** claim to defeat modern deep-learning facial recognition (e.g., ArcFace/AdaFace), prevent deepfakes, or guarantee anonymity. Those are open research questions requiring independent validation against threat-specific models.
* **Visual Similarity vs. Privacy Protection**: Full-image and regional SSIM/PSNR measure human viewing quality and signal distortion only; they do not measure identity protection.
* **Pixel Change vs. Anonymity**: Modifying pixels inside a bounding box (`L1 diff > 0`) does not automatically protect privacy. VIGIL reports pixel modification coverage separately from empirical detector retention.
* **Local Detector Retention Scope**: Pre/post detection retention tests run the local OpenCV Haar cascades (`haarcascade_frontalface_default`, `haarcascade_profileface`, `haarcascade_russian_plate_number`), `cv2.QRCodeDetector`, and morphological gradient text detectors. A `0%` retention ratio on a Haar cascade does **not** imply suppression on deep neural detectors.
* **Controlled Transformation Scope**: JPEG Q=75 compression, 0.5x resizing, and 3x3 Gaussian blur tests measure how much of the applied perturbation amplitude survives standard image degradation — not resistance to biometric recognition.
* **Explicit Fallback Mode Disclosure**: When `replace_this_file.pt` is `0 bytes` (placeholder), VIGIL never fabricates neural predictions. It explicitly reports `FALLBACK_HEURISTIC_MODE` in the UI banner and JSON audit reports, using geometric anatomical priors inside detected face boxes.

---

## Hardware Optimization (AMD Athlon 3000G / 8 GB RAM / Vega Integrated Graphics)

VIGIL is engineered for CPU-first execution on constrained hardware:
* **CPU Thread Bounding**: Caps PyTorch intra-op threads to `min(2, os.cpu_count())` to prevent thread contention on dual-core / 4-thread processors.
* **Lightweight Neural Architecture (< 100M Parameters)**: `VigilPrivacyNet` (`MobileNetV3-Large` encoder + U-Net decoder) has **6,394,127 parameters** (~6.39M parameters, ~26 MB in FP32) — over 15× smaller than the 100M parameter ceiling.
* **Lazy Model Loading**: PyTorch weights are loaded only when an image analysis request arrives and can hot-reload when `replace_this_file.pt` is replaced on disk.
* **Resolution & Session Guardrails**: Automatically bounds working image dimensions to `1600px` by default (configurable per upload), caps simultaneous in-RAM sessions to `3`, and provides explicit session memory purging (`DELETE /api/sessions/{session_id}` + `gc.collect()`).

---

## Installation & Quick Start

### 1. Create the Project & Placeholder Weights File
```bash
cd VIGIL
touch replace_this_file.pt
```
*(Leave `replace_this_file.pt` at 0 bytes to run in explicit `FALLBACK_HEURISTIC_MODE`, or replace it with your trained `.pt` checkpoint at any time.)*

### 2. Install CPU-Only PyTorch & Dependencies
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### 3. Run the Unit Test Suite
```bash
pytest -v tests/test_vigil_pipeline.py
```

### 4. Start the VIGIL Application Server
```bash
uvicorn vigil_app.main:app --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser to access the 6-view VIGIL interface (**Overview**, **Workspace**, **Detection**, **VIGIL Lab**, **Audit**, **Export**).

---

## Training the AI Model End-to-End & Applying Seeded Gaussian Noise

To train `VigilPrivacyNet` (~6.39M parameters) end-to-end and generate `replace_this_file.pt`:
```bash
pip install datasets transformers pillow
python train_vigil_model.py --mode train --epochs 5 --batch-size 8 --output replace_this_file.pt
```

To run standalone CLI sensitive-region recognition followed by seeded Gaussian noise injection:
```bash
python train_vigil_model.py --mode infer --input sample.jpg --output protected.png --sigma 22.0 --seed 42
```

---

## Directory Structure
```
VIGIL/
├── replace_this_file.pt            # 0-byte placeholder (or trained weights)
├── requirements.txt
├── README.md
├── train_vigil_model.py
├── vigil_app/
│   ├── __init__.py
│   ├── config.py                   # Hardware-constrained settings
│   ├── schemas.py                  # Strict Pydantic schemas (snake_case keys)
│   ├── main.py                     # FastAPI application
│   ├── models/
│   │   ├── __init__.py
│   │   └── privacy_net.py          # VigilPrivacyNet (~6.39M params) + lazy loader
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── perception_engine.py    # Face/QR/Text/Plate detection + seg
│   │   ├── privacy_engine.py       # Mask + transformations (fixed exclusion)
│   │   ├── evaluation_engine.py    # SSIM/PSNR + controlled transforms
│   │   ├── security_engine.py      # PNG chunk sanitizer + sessions
│   │   ├── audit_engine.py         # Honest audit reports
│   │   └── vigil_core.py           # Central orchestrator
│   └── static/
│       ├── index.html              # 6-view dashboard
│       ├── styles.css
│       └── app.js                  # Frontend controller
└── tests/
    └── test_vigil_pipeline.py
```
