# vigil_app/engines/perception_engine.py
"""
VIGIL Perception Engine
Detects faces, QR codes, text regions, and licence plates on CPU with explicit
detector provenance, confidence estimates, and 7-class semantic segmentation.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

from vigil_app.config import SEMANTIC_CLASSES
from vigil_app.models.privacy_net import MODEL_MANAGER
from vigil_app.schemas import BoundingBox, DetectedRegion


def _compute_iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    x_a = max(box_a[0], box_b[0])
    y_a = max(box_a[1], box_b[1])
    x_b = min(box_a[2], box_b[2])
    y_b = min(box_a[3], box_b[3])

    inter_w = max(0, x_b - x_a)
    inter_h = max(0, y_b - y_a)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0

    area_a = max(1, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
    area_b = max(1, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
    return float(inter_area / float(area_a + area_b - inter_area))


def _nms_boxes(
    boxes_with_scores: List[Tuple[int, int, int, int, float, str]],
    iou_threshold: float = 0.35,
) -> List[Tuple[int, int, int, int, float, str]]:
    if not boxes_with_scores:
        return []
    ordered = sorted(boxes_with_scores, key=lambda item: item[4], reverse=True)
    kept: List[Tuple[int, int, int, int, float, str]] = []
    for candidate in ordered:
        c_box = candidate[:4]
        if all(_compute_iou(c_box, existing[:4]) < iou_threshold for existing in kept):
            kept.append(candidate)
    return kept


class PerceptionEngine:
    """CPU-optimized multi-category sensitive region perception engine."""

    def __init__(self) -> None:
        haar_dir = cv2.data.haarcascades
        self._frontal_face_path = os.path.join(haar_dir, "haarcascade_frontalface_default.xml")
        self._profile_face_path = os.path.join(haar_dir, "haarcascade_profileface.xml")
        self._plate_path = os.path.join(haar_dir, "haarcascade_russian_plate_number.xml")

        self._frontal_cascade = cv2.CascadeClassifier(self._frontal_face_path)
        self._profile_cascade = cv2.CascadeClassifier(self._profile_face_path)
        self._plate_cascade = (
            cv2.CascadeClassifier(self._plate_path)
            if os.path.exists(self._plate_path)
            else None
        )
        self._qr_detector = cv2.QRCodeDetector()

    def detect_faces(self, gray: np.ndarray) -> List[Tuple[int, int, int, int, float, str]]:
        h, w = gray.shape[:2]
        min_dim = max(28, int(min(h, w) * 0.05))
        candidates: List[Tuple[int, int, int, int, float, str]] = []

        if not self._frontal_cascade.empty():
            boxes, reject_levels, level_weights = self._frontal_cascade.detectMultiScale3(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(min_dim, min_dim),
                outputRejectLevels=True,
            )
            if len(boxes) > 0:
                for (x, y, bw, bh), weight in zip(boxes, level_weights):
                    w_val = float(weight[0]) if isinstance(weight, (list, np.ndarray)) else float(weight)
                    conf = float(np.clip(0.55 + 0.08 * w_val, 0.50, 0.98))
                    candidates.append((int(x), int(y), int(x + bw), int(y + bh), round(conf, 3), "OpenCV_Haar_FrontalFace"))

        if not self._profile_cascade.empty():
            p_boxes = self._profile_cascade.detectMultiScale(
                gray, scaleFactor=1.12, minNeighbors=5, minSize=(min_dim, min_dim)
            )
            for (x, y, bw, bh) in p_boxes:
                candidates.append((int(x), int(y), int(x + bw), int(y + bh), 0.72, "OpenCV_Haar_ProfileFace"))

        return _nms_boxes(candidates, iou_threshold=0.35)

    def detect_qr_codes(self, rgb: np.ndarray) -> List[Tuple[int, int, int, int, float, str]]:
        h, w = rgb.shape[:2]
        results: List[Tuple[int, int, int, int, float, str]] = []
        try:
            ok, decoded_info, points, _ = self._qr_detector.detectAndDecodeMulti(rgb)
            if ok and points is not None:
                for idx, pts in enumerate(points):
                    pts_i = pts.astype(np.int32)
                    x1 = int(np.clip(pts_i[:, 0].min() - 4, 0, w - 1))
                    y1 = int(np.clip(pts_i[:, 1].min() - 4, 0, h - 1))
                    x2 = int(np.clip(pts_i[:, 0].max() + 4, 0, w))
                    y2 = int(np.clip(pts_i[:, 1].max() + 4, 0, h))
                    if x2 > x1 + 8 and y2 > y1 + 8:
                        has_payload = bool(decoded_info and idx < len(decoded_info) and decoded_info[idx])
                        conf = 0.98 if has_payload else 0.85
                        results.append((x1, y1, x2, y2, conf, "OpenCV_QRCodeDetector"))
        except cv2.error:
            pass
        return _nms_boxes(results, iou_threshold=0.3)

    def detect_licence_plates(
        self,
        gray: np.ndarray,
        existing_boxes: List[Tuple[int, int, int, int]],
    ) -> List[Tuple[int, int, int, int, float, str]]:
        candidates: List[Tuple[int, int, int, int, float, str]] = []

        if self._plate_cascade is not None and not self._plate_cascade.empty():
            plates = self._plate_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 14)
            )
            for (x, y, bw, bh) in plates:
                box = (int(x), int(y), int(x + bw), int(y + bh))
                if all(_compute_iou(box, eb) < 0.25 for eb in existing_boxes):
                    candidates.append((*box, 0.78, "OpenCV_Haar_LicencePlate"))

        return _nms_boxes(candidates, iou_threshold=0.3)

    def detect_text_regions(
        self,
        gray: np.ndarray,
        existing_boxes: List[Tuple[int, int, int, int]],
    ) -> List[Tuple[int, int, int, int, float, str]]:
        """Morphological horizontal gradient text-line detector."""
        h, w = gray.shape[:2]
        grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
        abs_grad_x = cv2.convertScaleAbs(grad_x)
        blurred = cv2.GaussianBlur(abs_grad_x, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, rect_kernel)
        contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: List[Tuple[int, int, int, int, float, str]] = []
        min_area = max(300, int(h * w * 0.0012))
        max_area = int(h * w * 0.18)

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            if area < min_area or area > max_area:
                continue
            aspect = bw / float(max(1, bh))
            if aspect < 2.2 or aspect > 18.0 or bh < 10 or bh > int(h * 0.22):
                continue

            roi = thresh[y : y + bh, x : x + bw]
            fill_density = float(np.count_nonzero(roi)) / float(max(1, area))
            if not (0.22 <= fill_density <= 0.78):
                continue

            box = (int(x), int(y), int(x + bw), int(y + bh))
            if any(_compute_iou(box, eb) > 0.15 for eb in existing_boxes):
                continue

            conf = round(float(np.clip(0.50 + 0.35 * fill_density, 0.52, 0.82)), 3)
            candidates.append((*box, conf, "Morphological_Gradient_TextDetector"))

        deduped = _nms_boxes(candidates, iou_threshold=0.25)
        return deduped[:8]

    def analyze_image(self, rgb_image: np.ndarray) -> Tuple[List[DetectedRegion], np.ndarray, Dict[str, Any]]:
        """Runs full perception pass: face/QR/plate/text detection + 7-class segmentation."""
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)

        face_raw = self.detect_faces(gray)
        qr_raw = self.detect_qr_codes(rgb_image)

        occupied_boxes: List[Tuple[int, int, int, int]] = [
            b[:4] for b in (face_raw + qr_raw)
        ]
        plate_raw = self.detect_licence_plates(gray, occupied_boxes)
        occupied_boxes.extend(b[:4] for b in plate_raw)
        text_raw = self.detect_text_regions(gray, occupied_boxes)

        face_bboxes_only = [b[:4] for b in face_raw]
        seg_mask, seg_meta = MODEL_MANAGER.predict_semantic_mask(rgb_image, face_bboxes_only)

        # If neural weights are loaded, extract connected components from the foreground mask
        if not seg_meta["is_fallback"]:
            fg_binary = (seg_mask > 0).astype(np.uint8) * 255
            num_labels, _, stats, _ = cv2.connectedComponentsWithStats(fg_binary)
            h, w = rgb_image.shape[:2]
            for lbl in range(1, num_labels):
                x, y, bw, bh, area = stats[lbl]
                if area >= max(400, int(h * w * 0.005)):
                    cand_box = (int(x), int(y), int(x + bw), int(y + bh))
                    if all(_compute_iou(cand_box, f[:4]) < 0.25 for f in face_raw):
                        face_raw.append((*cand_box, 0.89, "VigilPrivacyNet_SemanticComponent"))

        regions: List[DetectedRegion] = []
        counter = 1

        def _append_regions(
            raw_list: List[Tuple[int, int, int, int, float, str]],
            category: str,
        ) -> None:
            nonlocal counter
            for (x1, y1, x2, y2, conf, source) in raw_list:
                roi_seg = seg_mask[y1:y2, x1:x2]
                unique_cls = [
                    SEMANTIC_CLASSES[int(c)]
                    for c in np.unique(roi_seg)
                    if int(c) in SEMANTIC_CLASSES and int(c) > 0
                ]
                regions.append(
                    DetectedRegion(
                        region_id=f"reg_{counter:03d}",
                        category=category,  # type: ignore[arg-type]
                        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                        confidence=conf,
                        detector_source=source,
                        active=True,
                        semantic_classes_present=unique_cls,
                        notes=(
                            "Fallback geometric sub-parts inside Haar box"
                            if (category == "face" and seg_meta["is_fallback"])
                            else "Detected region"
                        ),
                    )
                )
                counter += 1

        _append_regions(face_raw, "face")
        _append_regions(qr_raw, "qr_code")
        _append_regions(plate_raw, "licence_plate")
        _append_regions(text_raw, "text")

        metadata = {
            "total_regions": len(regions),
            "counts_by_category": {
                "face": len(face_raw),
                "qr_code": len(qr_raw),
                "licence_plate": len(plate_raw),
                "text": len(text_raw),
            },
            "segmentation": seg_meta,
            "model_status": MODEL_MANAGER.get_status(),
        }
        return regions, seg_mask, metadata


PERCEPTION_ENGINE = PerceptionEngine()
