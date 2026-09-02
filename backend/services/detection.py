"""CV Detection Service for FoodFlow AI.

Loads fine-tuned YOLOv8 weights to detect dish-wise leftover food from plate return images,
estimates leftover quantities in grams, and renders annotated bounding boxes.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session
from ultralytics import YOLO

from backend import models

REPO_ROOT = Path(__file__).resolve().parents[2]
SOUTH_INDIAN_WEIGHTS = (
    REPO_ROOT / "runs" / "detect" / "train-south-indian" / "weights" / "best.pt"
)
BASE_WEIGHTS = REPO_ROOT / "yolov8n.pt"

# Estimated typical full portion weight (grams) per dish class
DEFAULT_PORTION_GRAMS = {
    "rice": 180.0,
    "sambar_rice": 160.0,
    "curd_rice": 140.0,
    "biryani": 200.0,
    "rasam": 80.0,
    "curry": 100.0,
    "potato_curry": 90.0,
    "green_curry": 90.0,
    "chicken": 100.0,
    "egg": 50.0,
    "salad": 60.0,
    "bonda": 80.0,
    "chips": 30.0,
    "sweet": 50.0,
}

_MODEL: YOLO | None = None


def get_yolo_model() -> YOLO:
    """Lazy load the fine-tuned YOLO model checkpoint."""
    global _MODEL
    if _MODEL is None:
        if SOUTH_INDIAN_WEIGHTS.is_file():
            print(f"Loading South Indian YOLO model from {SOUTH_INDIAN_WEIGHTS}")
            _MODEL = YOLO(str(SOUTH_INDIAN_WEIGHTS))
        elif BASE_WEIGHTS.is_file():
            print(f"South Indian model not found. Falling back to base YOLO from {BASE_WEIGHTS}")
            _MODEL = YOLO(str(BASE_WEIGHTS))
        else:
            raise FileNotFoundError(
                f"No YOLO model weights found at {SOUTH_INDIAN_WEIGHTS} or {BASE_WEIGHTS}."
            )
    return _MODEL


def estimate_leftover_grams(
    cv_class: str, box_area_fraction: float, confidence: float
) -> float:
    """Estimate wasted grams based on detected dish class and bounding box size ratio."""
    base_g = DEFAULT_PORTION_GRAMS.get(cv_class, 100.0)
    # Scaled area heuristic: full tray dish area ratio is ~0.15 - 0.35 of total frame
    # We map area fraction to estimated leftover weight, bounded between 15% and 100% of base portion
    ratio = min(max(box_area_fraction * 3.2, 0.15), 1.0)
    est_g = round(base_g * ratio / 5.0) * 5.0
    return float(max(est_g, 10.0))


def process_plate_image(
    image_bytes: bytes, db: Session, conf_threshold: float = 0.25
) -> dict[str, Any]:
    """Run object detection on raw image bytes, return detections and annotated image."""
    model = get_yolo_model()

    # Decode image bytes to OpenCV BGR numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Invalid image file format or corrupted bytes.")

    img_h, img_w = img_bgr.shape[:2]
    img_area = float(img_h * img_w)

    # Run inference
    results = model(img_bgr, conf=conf_threshold, verbose=False)
    boxes = results[0].boxes if len(results) > 0 else []

    # Map database dishes by cv_class and by name (lowercased)
    active_dishes = db.query(models.Dish).filter(models.Dish.is_active.is_(True)).all()
    dish_by_cv_class = {d.cv_class.lower(): d for d in active_dishes if d.cv_class}
    dish_by_name = {d.name.lower().replace(" ", "_"): d for d in active_dishes}

    detections = []
    annotated_bgr = img_bgr.copy()

    for box in boxes:
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        cls_name = model.names.get(cls_id, f"class_{cls_id}").lower()

        # Bounding box coordinates
        xyxy = box.xyxy[0].tolist()
        x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        box_area_frac = (w * h) / img_area if img_area > 0 else 0.0

        # Find matching dish in DB
        matched_dish = dish_by_cv_class.get(cls_name) or dish_by_name.get(cls_name)
        dish_id = matched_dish.id if matched_dish else None
        dish_name = matched_dish.name if matched_dish else cls_name.replace("_", " ").title()

        est_grams = estimate_leftover_grams(cls_name, box_area_frac, conf)

        detections.append(
            {
                "dish_id": dish_id,
                "dish_name": dish_name,
                "cv_class": cls_name,
                "confidence": round(conf, 3),
                "estimated_wasted_grams": est_grams,
                "bbox": [x1, y1, x2, y2],
                "box_area_fraction": round(box_area_frac, 4),
            }
        )

        # Draw bounding box and label on annotated image
        cv2.rectangle(annotated_bgr, (x1, y1), (x2, y2), (16, 185, 129), 2)
        label = f"{dish_name} {conf:.0%} ({int(est_grams)}g)"
        
        # Draw background text box for readability
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated_bgr, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, y1), (16, 185, 129), -1)
        cv2.putText(
            annotated_bgr,
            label,
            (x1 + 3, max(th + 2, y1 - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    # Encode annotated image to Base64 JPEG
    _, buffer = cv2.imencode(".jpg", annotated_bgr)
    annotated_b64 = base64.b64encode(buffer).decode("utf-8")

    total_est_wasted_g = sum(d["estimated_wasted_grams"] for d in detections)

    return {
        "detected_count": len(detections),
        "total_estimated_wasted_grams": total_est_wasted_g,
        "detections": detections,
        "annotated_image_b64": f"data:image/jpeg;base64,{annotated_b64}",
    }
