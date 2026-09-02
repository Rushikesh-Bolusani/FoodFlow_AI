"""FastAPI router for Computer Vision plate return detection."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db
from backend.services.detection import process_plate_image

router = APIRouter(prefix="/api", tags=["detection"])


@router.post("/detect")
async def detect_plate_leftovers(
    file: UploadFile = File(...),
    site_id: int = Query(default=1, description="ID of cafeteria / kitchen site"),
    meal: str = Query(default="lunch", description="Meal type: breakfast, lunch, snacks, dinner"),
    save_record: bool = Query(
        default=False, description="Automatically persist detected leftovers to database waste records"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Process a food tray / plate return image with YOLOv8.

    Detects food items, estimates leftover quantities, and optionally saves waste records.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image (JPEG, PNG, WebP).")

    site = db.get(models.Site, site_id)
    if not site:
        site = db.query(models.Site).first()
        if not site:
            site = models.Site(name="Hostel 1", location="Hostel Block 1 Mess")
            db.add(site)
            db.commit()
            db.refresh(site)

    try:
        contents = await file.read()
        results = process_plate_image(contents, db=db)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Plate detection failed: {err}")

    created_records = []
    if save_record and results["detections"]:
        today = date.today()
        for det in results["detections"]:
            dish_id = det.get("dish_id")
            if not dish_id:
                # If dish was not directly mapped by cv_class, fallback to generic or search by name
                dish_name = det.get("dish_name")
                existing = (
                    db.query(models.Dish)
                    .filter(models.Dish.name.ilike(f"%{dish_name}%"))
                    .first()
                )
                if existing:
                    dish_id = existing.id

            if dish_id:
                rec = models.WasteRecord(
                    site_id=site_id,
                    dish_id=dish_id,
                    meal=meal,
                    record_date=today,
                    wasted_grams=det["estimated_wasted_grams"],
                    prep_grams=det["estimated_wasted_grams"] * 4.0,  # Estimated prep baseline
                    source="cv_camera",
                )
                db.add(rec)
                db.flush()
                created_records.append(
                    {
                        "record_id": rec.id,
                        "dish_id": dish_id,
                        "dish_name": det["dish_name"],
                        "wasted_grams": rec.wasted_grams,
                    }
                )

        db.commit()

    results["saved_records"] = created_records
    results["site_id"] = site_id
    results["site_name"] = site.name
    results["meal"] = meal
    return results
