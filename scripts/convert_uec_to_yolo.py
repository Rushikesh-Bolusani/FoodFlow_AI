from pathlib import Path
import random
import shutil
from PIL import Image

# =========================
# PATHS
# =========================

DATASET_ROOT = Path(
    r"D:\FoodFLow_AI\dataset\foodflowdataset\UECFOOD256"
)

OUTPUT_ROOT = Path(
    r"D:\FoodFLow_AI\dataset\yolo_food"
)

TRAIN_RATIO = 0.8
SEED = 42

random.seed(SEED)


# =========================
# CREATE OUTPUT DIRECTORIES
# =========================

for folder in [
    OUTPUT_ROOT / "images" / "train",
    OUTPUT_ROOT / "images" / "val",
    OUTPUT_ROOT / "labels" / "train",
    OUTPUT_ROOT / "labels" / "val",
]:
    folder.mkdir(parents=True, exist_ok=True)


# =========================
# FIND CATEGORIES
# =========================

categories = []

for folder in DATASET_ROOT.iterdir():
    if folder.is_dir() and (folder / "bb_info.txt").exists():
        try:
            category_id = int(folder.name)
            categories.append((category_id, folder))
        except ValueError:
            pass

categories.sort()

print(f"Annotated categories found: {len(categories)}")


# =========================
# CATEGORY MAPPING
# =========================
# UEC category IDs may not be continuous.
# YOLO needs class IDs starting from 0.

category_to_yolo = {
    category_id: index
    for index, (category_id, _) in enumerate(categories)
}


# =========================
# PROCESS DATASET
# =========================

total_images = 0
total_annotations = 0

for category_id, category_folder in categories:

    bb_file = category_folder / "bb_info.txt"

    with open(bb_file, "r", encoding="utf-8") as f:
        lines = f.readlines()[1:]  # skip header

    records = []

    for line in lines:
        parts = line.strip().split()

        if len(parts) != 5:
            continue

        try:
            image_id = parts[0]
            x1 = float(parts[1])
            y1 = float(parts[2])
            x2 = float(parts[3])
            y2 = float(parts[4])
        except ValueError:
            continue

        image_path = category_folder / f"{image_id}.jpg"

        if not image_path.exists():
            continue

        records.append(
            (image_path, x1, y1, x2, y2)
        )

    random.shuffle(records)

    split_index = int(len(records) * TRAIN_RATIO)

    train_records = records[:split_index]
    val_records = records[split_index:]

    yolo_class = category_to_yolo[category_id]

    for split, split_records in [
        ("train", train_records),
        ("val", val_records),
    ]:

        for image_path, x1, y1, x2, y2 in split_records:

            # Make unique filename because different categories
            # can contain the same image filename.
            filename = f"class{category_id}_{image_path.name}"

            destination_image = (
                OUTPUT_ROOT / "images" / split / filename
            )

            destination_label = (
                OUTPUT_ROOT
                / "labels"
                / split
                / f"{Path(filename).stem}.txt"
            )

            # Read image dimensions
            try:
                with Image.open(image_path) as img:
                    image_width, image_height = img.size
            except Exception:
                continue

            # Convert bounding box to YOLO format
            box_width = x2 - x1
            box_height = y2 - y1

            x_center = x1 + box_width / 2
            y_center = y1 + box_height / 2

            # Normalize
            x_center /= image_width
            y_center /= image_height
            box_width /= image_width
            box_height /= image_height

            # Copy image
            shutil.copy2(
                image_path,
                destination_image
            )

            # Write YOLO annotation
            with open(
                destination_label,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    f"{yolo_class} "
                    f"{x_center:.6f} "
                    f"{y_center:.6f} "
                    f"{box_width:.6f} "
                    f"{box_height:.6f}\n"
                )

            total_images += 1
            total_annotations += 1


print()
print("================================")
print("CONVERSION COMPLETE")
print("================================")
print(f"Images processed: {total_images}")
print(f"Annotations created: {total_annotations}")
print(f"Output: {OUTPUT_ROOT}")