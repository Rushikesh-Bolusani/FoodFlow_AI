"""Multi-site benchmarking API endpoints."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["benchmarks"])


@router.get("/benchmarks", response_model=list[schemas.SiteBenchmarkOut])
def get_site_benchmarks(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Compare performance metrics across all kitchen sites."""
    sites = db.query(models.Site).all()
    cutoff_date = date.today() - timedelta(days=days)

    benchmarks = []

    for site in sites:
        records = (
            db.query(models.WasteRecord)
            .filter(
                models.WasteRecord.site_id == site.id,
                models.WasteRecord.record_date >= cutoff_date,
            )
            .all()
        )

        att_records = (
            db.query(models.Attendance)
            .filter(
                models.Attendance.site_id == site.id,
                models.Attendance.day >= cutoff_date,
            )
            .all()
        )

        total_diners = sum(a.headcount for a in att_records) if att_records else 1

        if not records:
            benchmarks.append(
                schemas.SiteBenchmarkOut(
                    site_id=site.id,
                    site_name=site.name,
                    total_waste_kg=0.0,
                    avg_daily_waste_kg=0.0,
                    waste_percentage=0.0,
                    total_cost_rupees=0.0,
                    total_diners=int(total_diners),
                    waste_per_diner_grams=0.0,
                    top_wasted_dish="None",
                )
            )
            continue

        total_wasted_g = sum(r.wasted_grams for r in records)
        total_prep_g = sum(r.prep_grams or 0.0 for r in records)
        
        # Calculate cost
        total_cost = 0.0
        dish_wastes = {}
        for r in records:
            if r.dish:
                total_cost += (r.wasted_grams / 100.0) * r.dish.cost_per_100g
                dish_wastes[r.dish.name] = dish_wastes.get(r.dish.name, 0.0) + r.wasted_grams

        top_dish = max(dish_wastes.items(), key=lambda x: x[1])[0] if dish_wastes else "N/A"

        days_count = len(set(r.record_date for r in records)) or 1

        total_waste_kg = total_wasted_g / 1000.0
        avg_daily_kg = total_waste_kg / days_count
        waste_pct = (total_wasted_g / total_prep_g * 100.0) if total_prep_g > 0 else 0.0
        waste_per_diner = (total_wasted_g / total_diners) if total_diners > 0 else 0.0

        benchmarks.append(
            schemas.SiteBenchmarkOut(
                site_id=site.id,
                site_name=site.name,
                total_waste_kg=round(total_waste_kg, 1),
                avg_daily_waste_kg=round(avg_daily_kg, 1),
                waste_percentage=round(waste_pct, 1),
                total_cost_rupees=round(total_cost, 0),
                total_diners=int(total_diners),
                waste_per_diner_grams=round(waste_per_diner, 1),
                top_wasted_dish=top_dish,
            )
        )

    return benchmarks
