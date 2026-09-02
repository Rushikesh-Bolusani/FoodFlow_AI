"""Impact & Nutrition conversion API endpoints."""

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["impact"])


@router.get("/impact", response_model=schemas.ImpactOut)
def get_impact_summary(
    site_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    """Calculate waste totals, cost lost in rupees, calories/protein lost, and CO2e emitted."""
    query = db.query(models.WasteRecord)
    if site_id is not None:
        query = query.filter(models.WasteRecord.site_id == site_id)
    if start is not None:
        query = query.filter(models.WasteRecord.record_date >= start)
    if end is not None:
        query = query.filter(models.WasteRecord.record_date <= end)

    records = query.all()

    if not records:
        return schemas.ImpactOut(
            total_waste_kg=0.0,
            total_prep_kg=0.0,
            waste_percentage=0.0,
            total_cost_rupees=0.0,
            total_calories_lost=0.0,
            total_protein_kg=0.0,
            total_co2e_kg=0.0,
            days_count=0,
        )

    total_wasted_g = 0.0
    total_prep_g = 0.0
    total_cost = 0.0
    total_calories = 0.0
    total_protein_g = 0.0
    total_co2e = 0.0
    unique_dates = set()

    for r in records:
        unique_dates.add(r.record_date)
        w_g = r.wasted_grams
        p_g = r.prep_grams or 0.0
        
        total_wasted_g += w_g
        total_prep_g += p_g

        dish = r.dish
        if dish:
            # All dish figures are per 100g
            factor = w_g / 100.0
            total_cost += factor * dish.cost_per_100g
            total_calories += factor * dish.calories_per_100g
            total_protein_g += factor * dish.protein_per_100g
            total_co2e += factor * dish.co2e_per_100g

    total_waste_kg = total_wasted_g / 1000.0
    total_prep_kg = total_prep_g / 1000.0
    waste_pct = (total_wasted_g / total_prep_g * 100.0) if total_prep_g > 0 else 0.0

    return schemas.ImpactOut(
        total_waste_kg=round(total_waste_kg, 1),
        total_prep_kg=round(total_prep_kg, 1),
        waste_percentage=round(waste_pct, 1),
        total_cost_rupees=round(total_cost, 0),
        total_calories_lost=round(total_calories, 0),
        total_protein_kg=round(total_protein_g / 1000.0, 2),
        total_co2e_kg=round(total_co2e, 1),
        days_count=len(unique_dates),
    )
