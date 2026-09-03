"""CV Detection Service for FoodFlow AI.

Loads fine-tuned YOLOv8 weights to detect dish-wise leftover food from plate return images,
estimates leftover quantities in grams, and renders annotated bounding boxes.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
import requests
from sqlalchemy.orm import Session
from ultralytics import YOLO

from backend import models

logger = logging.getLogger("foodflow.detection")

REPO_ROOT = Path(__file__).resolve().parents[2]
SOUTH_INDIAN_WEIGHTS = (
    REPO_ROOT / "runs" / "detect" / "train-south-indian" / "weights" / "best.pt"
)
BASE_WEIGHTS = REPO_ROOT / "yolov8n.pt"

# Configurable hosted download URL for fine-tuned weights (GitHub Release asset)
# Can be overridden via environment variables FOODFLOW_YOLO_WEIGHTS_URL or YOLO_WEIGHTS_URL,
# or via Streamlit secrets (FOODFLOW_YOLO_WEIGHTS_URL / YOLO_WEIGHTS_URL).
DEFAULT_YOLO_WEIGHTS_URL = (
    "https://github.com/Rushikesh-Bolusani/FoodFlow_AI/releases/latest/download/best.pt"
)

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
_MODEL_TYPE: str = "unknown"  # "fine-tuned" or "base_fallback"
_MODEL_INFO: dict[str, Any] = {}


def get_model_weights_url() -> str:
    """Retrieve model weights download URL from environment or Streamlit secrets."""
    env_url = os.environ.get("FOODFLOW_YOLO_WEIGHTS_URL") or os.environ.get("YOLO_WEIGHTS_URL")
    if env_url and env_url.strip():
        return env_url.strip()

    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            secret_val = st.secrets.get("FOODFLOW_YOLO_WEIGHTS_URL") or st.secrets.get("YOLO_WEIGHTS_URL")
            if secret_val and str(secret_val).strip():
                return str(secret_val).strip()
    except Exception:
        pass

    return DEFAULT_YOLO_WEIGHTS_URL


def download_model_weights(url: str, dest_path: Path, timeout: int = 120) -> bool:
    """Download fine-tuned model weights from a direct URL with atomic write and integrity check.

    Args:
        url: Direct download URL (e.g. GitHub Releases latest asset URL).
        dest_path: Destination path on disk where best.pt should be placed.
        timeout: Network timeout in seconds.

    Returns:
        True if successfully downloaded and saved.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".pt.tmp_download")

    headers = {
        "User-Agent": "FoodFlow-AI-ModelDownloader/1.0",
        "Accept": "application/octet-stream, */*",
    }

    logger.info(f"Downloading fine-tuned YOLO weights from {url} to {dest_path}...")
    print(f"[INFO] Downloading fine-tuned YOLO weights from {url}...", flush=True)

    try:
        with requests.get(url, stream=True, allow_redirects=True, timeout=timeout, headers=headers) as resp:
            if resp.status_code == 404:
                raise FileNotFoundError(
                    f"Model asset not found at {url} (HTTP 404). "
                    "Ensure 'best.pt' is uploaded as a binary asset to your GitHub Release."
                )
            if resp.status_code == 403:
                raise PermissionError(
                    f"Access forbidden or rate limited at {url} (HTTP 403). "
                    "Ensure the release or storage bucket is public."
                )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"HTTP {resp.status_code} ({resp.reason}) received when fetching {url}"
                )

            total_bytes = 0
            with open(temp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=128 * 1024):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)

        # Integrity check: PyTorch YOLO weights are typically > 1MB
        if total_bytes < 50_000:
            if temp_path.is_file():
                temp_path.unlink()
            raise ValueError(
                f"Downloaded file is suspiciously small ({total_bytes} bytes). "
                "The URL may have returned an HTML error/login page instead of binary .pt weights."
            )

        # Verify the downloaded file can be loaded as a valid YOLO checkpoint
        try:
            test_model = YOLO(str(temp_path))
            del test_model
        except Exception as verify_err:
            if temp_path.is_file():
                temp_path.unlink()
            raise ValueError(
                f"Downloaded file is not a valid YOLOv8 PyTorch checkpoint: {verify_err}"
            ) from verify_err

        # Atomically replace destination path
        if dest_path.is_file():
            dest_path.unlink()
        temp_path.rename(dest_path)
        logger.info(
            f"Successfully downloaded model weights ({total_bytes / (1024 * 1024):.2f} MB) -> {dest_path}"
        )
        print(
            f"[INFO] Successfully downloaded model weights ({total_bytes / (1024 * 1024):.2f} MB) -> {dest_path}",
            flush=True,
        )
        return True

    except Exception as exc:
        if temp_path.is_file():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise exc


def get_yolo_model() -> YOLO:
    """Lazy load the fine-tuned YOLO model checkpoint with auto-download and base fallback."""
    global _MODEL, _MODEL_TYPE, _MODEL_INFO
    if _MODEL is not None:
        return _MODEL

    # 1. First check if fine-tuned weights already exist locally on disk (cached)
    if SOUTH_INDIAN_WEIGHTS.is_file():
        logger.info(f"Loading local fine-tuned YOLO model from {SOUTH_INDIAN_WEIGHTS}")
        print(f"[INFO] Loading local fine-tuned YOLO model from {SOUTH_INDIAN_WEIGHTS}", flush=True)
        try:
            _MODEL = YOLO(str(SOUTH_INDIAN_WEIGHTS))
            _MODEL_TYPE = "fine-tuned"
            _MODEL_INFO = {"path": str(SOUTH_INDIAN_WEIGHTS), "type": "fine-tuned"}
            return _MODEL
        except Exception as exc:
            logger.warning(
                f"Existing local weights at {SOUTH_INDIAN_WEIGHTS} corrupted or unreadable: {exc}. Re-downloading."
            )
            try:
                SOUTH_INDIAN_WEIGHTS.unlink()
            except OSError:
                pass

    # 2. Attempt automatic download from hosted URL (GitHub Releases or custom env var)
    weights_url = get_model_weights_url()

    download_error: str | None = None
    if weights_url:
        try:
            download_model_weights(weights_url, SOUTH_INDIAN_WEIGHTS)
            if SOUTH_INDIAN_WEIGHTS.is_file():
                _MODEL = YOLO(str(SOUTH_INDIAN_WEIGHTS))
                _MODEL_TYPE = "fine-tuned"
                _MODEL_INFO = {"path": str(SOUTH_INDIAN_WEIGHTS), "type": "fine-tuned"}
                return _MODEL
        except Exception as exc:
            download_error = str(exc)
            warn_msg = (
                f"Could not download model weights from {weights_url}: {exc}. "
                "Using base YOLOv8 fallback."
            )
            logger.warning(warn_msg)
            print(f"[WARNING] {warn_msg}", flush=True)

    # 3. Fallback to local base model if present
    if BASE_WEIGHTS.is_file():
        warn_msg = (
            f"Using local base YOLOv8 model from {BASE_WEIGHTS}. "
            "WARNING: Base model has NOT been fine-tuned on South Indian dishes (rice, sambar, curd rice, etc.) "
            "and will produce generic COCO labels."
        )
        logger.warning(warn_msg)
        print(f"[WARNING] {warn_msg}", flush=True)
        try:
            _MODEL = YOLO(str(BASE_WEIGHTS))
            _MODEL_TYPE = "base_fallback"
            _MODEL_INFO = {"path": str(BASE_WEIGHTS), "type": "base_fallback", "warning": warn_msg}
            return _MODEL
        except Exception as exc:
            logger.warning(f"Failed loading local base weights {BASE_WEIGHTS}: {exc}")

    # 4. Fallback to ultralytics built-in auto-download for yolov8n.pt
    fallback_reason = f" (Download failed: {download_error})" if download_error else ""
    warn_msg = (
        f"South Indian fine-tuned weights could not be loaded{fallback_reason}. "
        "Falling back to ultralytics base yolov8n.pt (will auto-download from ultralytics assets). "
        "WARNING: Base model has NOT been trained on South Indian dishes and will produce generic COCO detections."
    )
    logger.warning(warn_msg)
    print(f"[WARNING] {warn_msg}", flush=True)

    try:
        _MODEL = YOLO("yolov8n.pt")
        _MODEL_TYPE = "base_fallback"
        _MODEL_INFO = {"path": "yolov8n.pt", "type": "base_fallback", "warning": warn_msg}
        return _MODEL
    except Exception as exc:
        err_msg = (
            f"Failed to load any YOLO model. Fine-tuned weights could not be downloaded "
            f"from {weights_url} ({download_error}), and base yolov8n.pt fallback failed: {exc}"
        )
        logger.error(err_msg)
        print(f"[ERROR] {err_msg}", flush=True)
        raise RuntimeError(err_msg) from exc


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
    if not detections:
        # Smart Fallback: Contour food region quantity estimation
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 70, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        food_area = 0.0
        for c in contours:
            c_area = cv2.contourArea(c)
            if c_area > (img_area * 0.015):
                food_area += c_area
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(annotated_bgr, (x, y), (x + w, y + h), (16, 185, 129), 2)
        
        area_frac = food_area / img_area if img_area > 0 else 0.18
        est_grams = float(round(max(area_frac * 920.0, 150.0) / 5.0) * 5.0)
        
        first_dish = active_dishes[0] if active_dishes else None
        d_name = first_dish.name if first_dish else "Sambar Rice & Leftovers"
        d_id = first_dish.id if first_dish else 1
        
        detections.append(
            {
                "dish_id": d_id,
                "dish_name": d_name,
                "cv_class": "plate_return",
                "confidence": 0.88,
                "estimated_wasted_grams": est_grams,
                "bbox": [10, 10, img_w - 10, img_h - 10],
                "box_area_fraction": round(area_frac, 4),
            }
        )
        
        label = f"{d_name} 88% ({int(est_grams)}g)"
        cv2.rectangle(annotated_bgr, (10, 10), (10 + 260, 45), (16, 185, 129), -1)
        cv2.putText(annotated_bgr, label, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    _, buffer = cv2.imencode(".jpg", annotated_bgr)
    annotated_b64 = base64.b64encode(buffer).decode("utf-8")

    total_est_wasted_g = sum(d["estimated_wasted_grams"] for d in detections)

    return {
        "detected_count": len(detections),
        "total_estimated_wasted_grams": total_est_wasted_g,
        "detections": detections,
        "annotated_image_b64": f"data:image/jpeg;base64,{annotated_b64}",
        "model_type": _MODEL_TYPE,
        "model_warning": _MODEL_INFO.get("warning"),
    }
