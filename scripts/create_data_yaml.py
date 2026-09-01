from pathlib import Path

dataset_root = Path(
    r"D:\FoodFLow_AI\dataset\foodflowdataset\UECFOOD256"
)

output_yaml = Path(
    r"D:\FoodFLow_AI\dataset\yolo_food\data.yaml"
)

# Read original category names
category_file = dataset_root / "category.txt"

categories = {}

with open(category_file, "r", encoding="utf-8") as f:
    next(f)  # skip header

    for line in f:
        parts = line.strip().split(maxsplit=1)

        if len(parts) == 2:
            category_id = int(parts[0])
            name = parts[1]
            categories[category_id] = name


# Find only categories that actually have annotations
annotated_categories = []

for folder in dataset_root.iterdir():

    if not folder.is_dir():
        continue

    try:
        category_id = int(folder.name)
    except ValueError:
        continue

    if (folder / "bb_info.txt").exists():
        annotated_categories.append(category_id)


annotated_categories.sort()


# Generate YAML
with open(output_yaml, "w", encoding="utf-8") as f:

    f.write("path: D:/FoodFLow_AI/dataset/yolo_food\n")
    f.write("train: images/train\n")
    f.write("val: images/val\n\n")

    f.write(f"nc: {len(annotated_categories)}\n")

    f.write("names:\n")

    for category_id in annotated_categories:
        name = categories.get(
            category_id,
            f"class_{category_id}"
        )

        # YAML-safe quoting
        name = name.replace("'", "''")

        f.write(f"  - '{name}'\n")


print(f"Created: {output_yaml}")
print(f"Number of classes: {len(annotated_categories)}")

print("\nClass mapping:")
for yolo_id, category_id in enumerate(annotated_categories):
    print(f"{yolo_id}: UEC {category_id} -> {categories.get(category_id)}")