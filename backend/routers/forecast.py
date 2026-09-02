"""Demand forecasting API endpoints."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import schemas
from backend.database import get_db
from forecasting import forecast

router = APIRouter(prefix="/api", tags=["forecast"])


@router.get("/forecast", response_model=list[schemas.ForecastItem])
def get_demand_forecast(
    site_id: int,
    target_date: date | None = None,
    db: Session = Depends(get_db),
):
    """Get next-day recommended cook quantities and attendance forecast for a site."""
    items = forecast.predict_next_day_demand(db, site_id=site_id, target_date=target_date)
    return items
