"""Menu Planner and Calendar Events API endpoints."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["menu"])


# ---------- Menu Planner ----------

@router.get("/menu", response_model=list[schemas.MenuPlanOut])
def list_menu_plans(
    site_id: int | None = None,
    day_of_week: int | None = Query(default=None, ge=0, le=6),
    db: Session = Depends(get_db),
):
    """Retrieve weekly menu plans."""
    query = db.query(models.MenuPlan).filter(models.MenuPlan.is_active.is_(True))
    if site_id is not None:
        query = query.filter(models.MenuPlan.site_id == site_id)
    if day_of_week is not None:
        query = query.filter(models.MenuPlan.day_of_week == day_of_week)

    items = query.all()
    output = []
    for m in items:
        out = schemas.MenuPlanOut.model_validate(m)
        out.site_name = m.site.name if m.site else ""
        out.dish_name = m.dish.name if m.dish else ""
        out.category = m.dish.category if m.dish else ""
        output.append(out)
    return output


@router.post("/menu", response_model=schemas.MenuPlanOut, status_code=201)
def create_menu_plan(payload: schemas.MenuPlanIn, db: Session = Depends(get_db)):
    """Add a dish to the weekly menu schedule."""
    existing = (
        db.query(models.MenuPlan)
        .filter(
            models.MenuPlan.site_id == payload.site_id,
            models.MenuPlan.day_of_week == payload.day_of_week,
            models.MenuPlan.meal == payload.meal,
            models.MenuPlan.dish_id == payload.dish_id,
        )
        .first()
    )
    if existing:
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        out = schemas.MenuPlanOut.model_validate(existing)
        out.site_name = existing.site.name if existing.site else ""
        out.dish_name = existing.dish.name if existing.dish else ""
        out.category = existing.dish.category if existing.dish else ""
        return out

    m = models.MenuPlan(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)

    out = schemas.MenuPlanOut.model_validate(m)
    out.site_name = m.site.name if m.site else ""
    out.dish_name = m.dish.name if m.dish else ""
    out.category = m.dish.category if m.dish else ""
    return out


@router.get("/menu/today", response_model=list[schemas.DishOut])
def get_today_menu(
    site_id: int | None = None,
    meal: str | None = None,
    db: Session = Depends(get_db),
):
    """Dynamic endpoint for QR feedback form: returns dishes served today."""
    today_dow = date.today().weekday()
    query = db.query(models.MenuPlan).filter(
        models.MenuPlan.day_of_week == today_dow,
        models.MenuPlan.is_active.is_(True),
    )
    if site_id is not None:
        query = query.filter(models.MenuPlan.site_id == site_id)
    if meal is not None:
        query = query.filter(models.MenuPlan.meal == meal)

    plans = query.all()

    if plans:
        dishes = [p.dish for p in plans if p.dish]
    else:
        # Fallback if no menu plan exists for today: return active dishes
        dish_query = db.query(models.Dish).filter(models.Dish.is_active.is_(True))
        if meal == "breakfast":
            dish_query = dish_query.filter(models.Dish.category == "breakfast")
        elif meal in ("lunch", "dinner"):
            dish_query = dish_query.filter(models.Dish.category.in_(["main", "side", "dessert", "non-veg"]))
        dishes = dish_query.all()

    return dishes


# ---------- Calendar Events ----------

@router.get("/calendar", response_model=list[schemas.CalendarEventOut])
def list_calendar_events(db: Session = Depends(get_db)):
    """Retrieve upcoming and historical calendar events."""
    events = (
        db.query(models.CalendarEvent)
        .order_by(models.CalendarEvent.event_date.asc())
        .all()
    )
    return events


@router.post("/calendar", response_model=schemas.CalendarEventOut, status_code=201)
def create_calendar_event(payload: schemas.CalendarEventIn, db: Session = Depends(get_db)):
    """Log a holiday, exam period, or special campus event."""
    evt = models.CalendarEvent(**payload.model_dump())
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt
