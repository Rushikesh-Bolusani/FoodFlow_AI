# FoodFlow AI — Project Instructions

Read this before doing anything in this repository.

## What this project is

FoodFlow AI is an end-to-end food waste intelligence platform for institutional
kitchens — cafeterias, hostels, hospitals, corporate canteens, and government
meal schemes (mid-day meal programs, railway catering, defense messes). It does
not just measure waste after the fact; it closes the loop from
**detection → understanding → prevention**.

## The core pipeline

1. **CV waste detection** — a camera above the plate-return area runs a
   fine-tuned YOLOv8 model to identify food items and estimate wasted quantity
   per dish, per meal, in real time.
2. **Diner feedback loop** — a QR code at the plate-return point lets diners
   tag *why* food was left (portion too big, taste, quality, not hungry, too
   spicy), pairing the "how much" from CV with the "why" from humans.
3. **Predictive demand forecasting** — next-day cooking quantities per dish
   from historical waste trends, attendance, day-of-week patterns, and
   institutional calendars (exams, holidays, events). Prophet / XGBoost.
4. **Waste → nutrition & cost conversion** — calories/protein lost, ₹ lost,
   CO₂e emitted, for ESG and stakeholder reporting.
5. **Multi-site benchmarking** — cross-cafeteria comparison dashboards
   identifying best and worst performing kitchens.
6. **Auto-generated recommendations** — operator dashboard suggesting portion
   size changes, menu swaps, and prep quantity adjustments.

## Current state of the repo

The CV stage is underway; everything else is yet to be built.

- `dataset/foodflowdataset/UECFOOD256` — source dataset (gitignored).
- `dataset/yolo_food/` — UECFOOD256 converted to YOLO format
  (~3.4k train images, train/val split 80/20, seed 42) with `data.yaml`.
- `dataset/indianfoodnet/` — Indian food dataset with its own `data.yaml`.
- `scripts/convert_uec_to_yolo.py` — UECFOOD256 bb_info.txt → YOLO labels.
- `scripts/create_data_yaml.py` — generates `dataset/yolo_food/data.yaml`
  from UEC category names.
- `runs/detect/train-*` — YOLOv8 training runs (gitignored). Latest run
  (`train-7`) fine-tuned on `indianfoodnet` starting from `train-6` weights:
  CPU device, imgsz 320, batch 8, epochs 10. Best weights at
  `runs/detect/train-7/weights/best.pt`.
- `yolov8n.pt` — base YOLOv8 nano model (gitignored via `*.pt`).

Not yet built: FastAPI backend, waste-record data model, inference service,
QR feedback flow, forecasting, dashboards.

## Tech stack (pinned in requirements.txt)

- **CV/AI:** ultralytics 8.4.x (YOLOv8) + torch 2.13 (CPU); ONNX/TensorRT
  for edge inference later.
- **Prototype input:** mobile phone camera (IP Webcam app or browser
  capture) + laptop inference — no special hardware for the demo.
- **Production target:** Jetson Nano / Raspberry Pi 4 + camera module.
- **Forecasting:** Prophet (installed; XGBoost optional).
- **Backend:** FastAPI + uvicorn. SQLite for dev, PostgreSQL for production.
  (Flask is also installed but FastAPI is the chosen API layer — do not add
  new Flask routes.)
- **Frontend:** Streamlit dashboards (installed) with plotly / matplotlib;
  React + Recharts only if the project later moves that way.

Environment: Windows, Git Bash shell, virtualenv at `./venv`. Training runs
so far are CPU-only with small imgsz/batch — keep new training commands
CPU-feasible unless asked otherwise.

## Conventions

- Match the existing script style in `scripts/`: plain runnable scripts,
  `# ===== SECTION =====` header comments, uppercase path constants,
  `pathlib.Path`, fixed seeds, and a clear printed summary at the end.
- Resolve paths relative to the repo root (e.g.
  `Path(__file__).resolve().parents[1]`), not hardcoded `D:\FoodFLow_AI\...`.
  The existing scripts and `data.yaml` use absolute Windows paths — don't
  copy that pattern into new code.
- Datasets, `runs/`, and `*.pt` are gitignored — never assume they exist on a
  fresh clone; guard file access with a clear message about what to prepare.
- Waste records are the central data model. Each record carries: site,
  meal (breakfast/lunch/dinner), date, dish, estimated quantity wasted,
  feedback reasons, and derived nutrition/cost/carbon figures.

## Working rules

- **Interfaces must be humanized.** Every UI, dashboard, and message should
  feel warm, clear, and human-written: plain language over jargon, friendly
  empty states, helpful error messages, readable charts with real labels
  (e.g. "You saved ₹4,200 this week", not "total_waste_delta=4.2e3").
  No robotic system-speak.
- Prefer incremental changes; explain what changed and why.
- Keep the prototype demoable with just a phone camera and a laptop — never
  add a hard dependency on edge hardware.
- Keep the CV pipeline modular so the same model code works with a phone
  stream now and a Jetson/Pi camera later (a `VideoSource` abstraction —
  webcam / IP stream / file — is the intended shape).
- If a request is ambiguous, make the most sensible choice for an
  institutional-kitchen user and state what was assumed.
- After building a feature, give exact run/demo instructions.
