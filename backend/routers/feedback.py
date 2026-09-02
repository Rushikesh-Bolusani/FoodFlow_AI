"""Diner QR code feedback API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=schemas.FeedbackOut, status_code=201)
def create_feedback(payload: schemas.FeedbackIn, db: Session = Depends(get_db)):
    """Log diner feedback submitted via QR code at plate return."""
    if payload.site_id:
        site = db.get(models.Site, payload.site_id)
        if not site:
            raise HTTPException(404, f"No site found with id {payload.site_id}")

    if payload.dish_id:
        dish = db.get(models.Dish, payload.dish_id)
        if not dish:
            raise HTTPException(404, f"No dish found with id {payload.dish_id}")

    fb = models.Feedback(
        site_id=payload.site_id,
        meal=payload.meal,
        dish_id=payload.dish_id,
        reasons=payload.reasons,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    res = schemas.FeedbackOut.model_validate(fb)
    if fb.site_id and (site := db.get(models.Site, fb.site_id)):
        res.site_name = site.name
    if fb.dish_id and (dish := db.get(models.Dish, fb.dish_id)):
        res.dish_name = dish.name
    return res


@router.get("/feedback", response_model=list[schemas.FeedbackOut])
def list_feedback(
    site_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve recent diner feedback submissions."""
    query = db.query(models.Feedback)
    if site_id is not None:
        query = query.filter(models.Feedback.site_id == site_id)

    items = query.order_by(models.Feedback.created_at.desc()).limit(limit).all()

    output = []
    for fb in items:
        res = schemas.FeedbackOut.model_validate(fb)
        if fb.site_id and (site := db.get(models.Site, fb.site_id)):
            res.site_name = site.name
        if fb.dish_id and (dish := db.get(models.Dish, fb.dish_id)):
            res.dish_name = dish.name
        output.append(res)

    return output


@router.get("/feedback/stats")
def get_feedback_stats(site_id: int | None = None, db: Session = Depends(get_db)):
    """Aggregate feedback reasons distribution for reporting."""
    query = db.query(models.Feedback)
    if site_id is not None:
        query = query.filter(models.Feedback.site_id == site_id)

    records = query.all()
    counts = {}
    ratings = [r.rating for r in records if r.rating]

    for r in records:
        for reason in r.reasons:
            counts[reason] = counts.get(reason, 0) + 1

    formatted = [
        {
            "reason_key": k,
            "reason_label": schemas.FEEDBACK_REASONS.get(k, k),
            "count": v,
        }
        for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]

    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

    return {
        "total_responses": len(records),
        "average_rating": avg_rating,
        "rated_responses": len(ratings),
        "reasons_breakdown": formatted,
    }
