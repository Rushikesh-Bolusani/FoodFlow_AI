"""Train YOLOv8 on the South Indian tray dataset.

Starts from yolov8n.pt (not IndianFoodNet weights) so the class head matches
the FoodFlow dish list. Writes a NEW run under runs/detect/ — existing runs
are left untouched.

Usage (from the repo root):
    venv/Scripts/python.exe scripts/train_south_indian.py
"""

from pathlib import Path

from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = REPO_ROOT / "dataset" / "south_indian_tray" / "data.yaml"
BASE_WEIGHTS = REPO_ROOT / "yolov8n.pt"


def main() -> None:
    if not DATA_YAML.is_file():
        raise FileNotFoundError(
            f"Missing {DATA_YAML}. Run scripts/prepare_south_indian_yolo.py first."
        )
    if not BASE_WEIGHTS.is_file():
        raise FileNotFoundError(
            f"Missing {BASE_WEIGHTS}. Place the YOLOv8 nano checkpoint in the repo root."
        )

    model = YOLO(str(BASE_WEIGHTS))
    results = model.train(
        data=str(DATA_YAML),
        epochs=40,
        imgsz=320,
        batch=8,
        device="cpu",
        workers=0,
        project=str(REPO_ROOT / "runs" / "detect"),
        name="train-south-indian",
        exist_ok=False,
        seed=42,
        pretrained=True,
    )
    print()
    print("================================")
    print("TRAINING FINISHED")
    print("================================")
    print(results)
    print("New weights (existing runs were not deleted):")
    print(f"  {REPO_ROOT / 'runs' / 'detect' / 'train-south-indian' / 'weights' / 'best.pt'}")


if __name__ == "__main__":
    main()
