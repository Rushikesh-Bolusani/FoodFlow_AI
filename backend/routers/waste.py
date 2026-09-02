"""Sites, dishes and waste records — the core data API."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["waste"])


# ---------- Sites ----------

@router.get("/sites", response_model=list[schemas.SiteOut])
def list_sites(db: Session = Depends(get_db)):
    return db.query(models.Site).order_by(models.Site.name).all()


@router.post("/sites", response_model=schemas.SiteOut, status_code=201)
def create_site(payload: schemas.SiteIn, db: Session = Depends(get_db)):
    existing = (
        db.query(models.Site)
        .filter(models.Site.name == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(
            409, f"A site called '{payload.name}' already exists"
        )
    site = models.Site(name=payload.name, location=payload.location)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


# ---------- Dishes ----------

@router.get("/dishes", response_model=list[schemas.DishOut])
def list_dishes(
    include_inactive: bool = False, db: Session = Depends(get_db)
):
    query = db.query(models.Dish)
    if not include_inactive:
        query = query.filter(models.Dish.is_active.is_(True))
    return query.order_by(models.Dish.name).all()


@router.post("/dishes", response_model=schemas.DishOut, status_code=201)
def create_dish(payload: schemas.DishIn, db: Session = Depends(get_db)):
    existing = (
        db.query(models.Dish).filter(models.Dish.name == payload.name).first()
    )
    if existing:
        raise HTTPException(
            409, f"A dish called '{payload.name}' already exists"
        )
    dish = models.Dish(**payload.model_dump())
    db.add(dish)
    db.commit()
    db.refresh(dish)
    return dish


# ---------- Waste records ----------

def _with_names(rec: models.WasteRecord) -> schemas.WasteRecordOut:
    item = schemas.WasteRecordOut.model_validate(rec)
    item.site_name = rec.site.name
    item.dish_name = rec.dish.name
    return item


@router.get("/waste", response_model=list[schemas.WasteRecordOut])
def list_waste(
    site_id: int | None = None,
    meal: schemas.Meal | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(models.WasteRecord)
    if site_id is not None:
        query = query.filter(models.WasteRecord.site_id == site_id)
    if meal is not None:
        query = query.filter(models.WasteRecord.meal == meal)
    if start is not None:
        query = query.filter(models.WasteRecord.record_date >= start)
    if end is not None:
        query = query.filter(models.WasteRecord.record_date <= end)
    records = (
        query.order_by(models.WasteRecord.record_date.desc())
        .limit(limit)
        .all()
    )
    return [_with_names(rec) for rec in records]


@router.post("/waste", response_model=schemas.WasteRecordOut, status_code=201)
def create_waste(
    payload: schemas.WasteRecordIn, db: Session = Depends(get_db)
):
    site = db.get(models.Site, payload.site_id)
    if not site:
        raise HTTPException(404, f"No site with id {payload.site_id}")
    dish = db.get(models.Dish, payload.dish_id)
    if not dish:
        raise HTTPException(404, f"No dish with id {payload.dish_id}")

    rec = models.WasteRecord(**payload.model_dump())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _with_names(rec)
