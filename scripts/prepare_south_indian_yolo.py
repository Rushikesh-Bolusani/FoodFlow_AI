"""Convert the Food Tray Detection COCO export into YOLO for FoodFlow AI.

Reads the Roboflow zip (does not delete it). Writes dataset/south_indian_tray/.
Merges max/min leftover tags into dish classes and drops generic labels.

Usage (from the repo root):
    venv/Scripts/python.exe scripts/prepare_south_indian_yolo.py
"""

from __future__ import annotations

import json
import shutil
import zipfile
from collections import Counter
from pathlib import Path

# ===== PATHS =====

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "dataset" / "south_indian_tray"
ZIP_CANDIDATES = [
    Path.home() / "Downloads" / "Food Tray Detection.v1i.coco.zip",
    REPO_ROOT / "dataset" / "Food Tray Detection.v1i.coco.zip",
]

# ===== CLASS MAP =====
# Raw Roboflow names -> FoodFlow dish class. None = skip.

CLASS_NAMES = [
    "rice",
    "sambar_rice",
    "curd_rice",
    "biryani",
    "rasam",
    "curry",
    "potato_curry",
    "green_curry",
    "chicken",
    "egg",
    "salad",
    "bonda",
    "chips",
    "sweet",
]

NAME_TO_ID = {name: i for i, name in enumerate(CLASS_NAMES)}

RAW_TO_CLASS = {
    "Biryani-max": "biryani",
    "Biryani-min": "biryani",
    "Bonda": "bonda",
    "Normal-Rice-max": "rice",
    "Normal-Rice-min": "rice",
    "Potato-dish": "potato_curry",
    "chicken-waste-max": "chicken",
    "chicken-waste-min": "chicken",
    "chips": "chips",
    "chips-max": "chips",
    "curd-rice-max": "curd_rice",
    "curd-rice-min": "curd_rice",
    "curry-dish": "curry",
    "curry-waste": "curry",
    "egg": "egg",
    "green-dish-curry": "green_curry",
    "rasam - max": "rasam",
    "rasam - min": "rasam",
    "salad": "salad",
    "sambar-rice-max": "sambar_rice",
    "sambar-rice-min": "sambar_rice",
    "sweet-brown": "sweet",
}


def find_zip() -> Path:
    for path in ZIP_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Could not find 'Food Tray Detection.v1i.coco.zip'. "
        "Place it in your Downloads folder or in dataset/."
    )


def coco_box_to_yolo(
    x: float, y: float, w: float, h: float, img_w: float, img_h: float
) -> tuple[float, float, float, float] | None:
    if img_w <= 0 or img_h <= 0 or w <= 0 or h <= 0:
        return None
    cx = (x + w / 2.0) / img_w
    cy = (y + h / 2.0) / img_h
    nw = w / img_w
    nh = h / img_h
    cx = min(max(cx, 0.0), 1.0)
    cy = min(max(cy, 0.0), 1.0)
    nw = min(max(nw, 0.0), 1.0)
    nh = min(max(nh, 0.0), 1.0)
    return cx, cy, nw, nh


def convert_split(zf: zipfile.ZipFile, split: str, counts: Counter) -> tuple[int, int]:
    ann_name = f"{split}/_annotations.coco.json"
    if ann_name not in zf.namelist():
        return 0, 0

    data = json.loads(zf.read(ann_name))
    cats = {c["id"]: c["name"] for c in data["categories"]}
    images = {im["id"]: im for im in data["images"]}

    by_image: dict[int, list] = {}
    skipped = 0
    kept = 0
    for ann in data["annotations"]:
        raw = cats.get(ann["category_id"], "")
        mapped = RAW_TO_CLASS.get(raw)
        if mapped is None:
            skipped += 1
            continue
        yolo_id = NAME_TO_ID[mapped]
        im = images.get(ann["image_id"])
        if not im:
            skipped += 1
            continue
        box = ann.get("bbox") or [0, 0, 0, 0]
        yolo = coco_box_to_yolo(
            float(box[0]),
            float(box[1]),
            float(box[2]),
            float(box[3]),
            float(im["width"]),
            float(im["height"]),
        )
        if yolo is None:
            skipped += 1
            continue
        by_image.setdefault(ann["image_id"], []).append((yolo_id, yolo))
        counts[mapped] += 1
        kept += 1

    img_dir = OUTPUT_ROOT / "images" / split
    lab_dir = OUTPUT_ROOT / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lab_dir.mkdir(parents=True, exist_ok=True)

    n_images = 0
    for image_id, boxes in by_image.items():
        im = images[image_id]
        src_name = f"{split}/{im['file_name']}"
        stem = Path(im["file_name"]).stem
        dest_img = img_dir / f"{stem}.jpg"
        dest_lab = lab_dir / f"{stem}.txt"
        with zf.open(src_name) as src, dest_img.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        lines = [
            f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
            for cls, (cx, cy, w, h) in boxes
        ]
        dest_lab.write_text("\n".join(lines) + "\n", encoding="utf-8")
        n_images += 1

    return n_images, skipped


def write_yaml() -> None:
    names_block = "\n".join(f"  {i}: {name}" for i, name in enumerate(CLASS_NAMES))
    text = (
        f"path: {OUTPUT_ROOT.as_posix()}\n"
        "train: images/train\n"
        "val: images/valid\n"
        "test: images/test\n"
        f"nc: {len(CLASS_NAMES)}\n"
        "names:\n"
        f"{names_block}\n"
    )
    (OUTPUT_ROOT / "data.yaml").write_text(text, encoding="utf-8")


def main() -> None:
    zip_path = find_zip()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    counts: Counter = Counter()
    print(f"Reading {zip_path}")
    with zipfile.ZipFile(zip_path) as zf:
        summary = {}
        for split in ("train", "valid", "test"):
            n_images, skipped = convert_split(zf, split, counts)
            summary[split] = (n_images, skipped)

    write_yaml()

    print()
    print("================================")
    print("SOUTH INDIAN TRAY DATASET READY")
    print("================================")
    print(f"Output: {OUTPUT_ROOT}")
    for split, (n_images, skipped) in summary.items():
        print(f"{split:6s}  images with dishes: {n_images:4d}  skipped boxes: {skipped}")
    print()
    print("Class box counts:")
    for name in CLASS_NAMES:
        print(f"  {counts[name]:5d}  {name}")
    print()
    print("Train with:")
    print(
        "  venv/Scripts/python.exe -m ultralytics cfg=default  "
        "(or see scripts/train_south_indian.py)"
    )


if __name__ == "__main__":
    main()
