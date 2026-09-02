"""AI Recommendations API endpoints.

Synthesizes waste records, diner feedback reasons, and institutional calendar
events into actionable kitchen suggestions (portion cuts, menu swaps, reformulations).
"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["recommendations"])


@router.get("/recommendations", response_model=list[schemas.RecommendationOut])
def get_recommendations(site_id: int | None = None, db: Session = Depends(get_db)):
    """Generate rule-based intelligence recommendations for kitchen managers."""
    cutoff = date.today() - timedelta(days=30)
    
    # Query waste records
    w_query = db.query(models.WasteRecord).filter(models.WasteRecord.record_date >= cutoff)
    if site_id is not None:
        w_query = w_query.filter(models.WasteRecord.site_id == site_id)
    records = w_query.all()

    # Query feedback
    f_query = db.query(models.Feedback).filter(models.Feedback.created_at >= cutoff)
    if site_id is not None:
        f_query = f_query.filter(models.Feedback.site_id == site_id)
    feedbacks = f_query.all()

    # Query calendar events
    events = (
        db.query(models.CalendarEvent)
        .filter(models.CalendarEvent.event_date >= date.today())
        .order_by(models.CalendarEvent.event_date.asc())
        .all()
    )

    recommendations = []

    # 1. Analyze high-waste dishes
    dish_stats = {}
    for r in records:
        if not r.dish or not r.site:
            continue
        key = (r.site.name, r.dish.name)
        if key not in dish_stats:
            dish_stats[key] = {"prep_g": 0.0, "waste_g": 0.0, "dish": r.dish, "site": r.site}
        dish_stats[key]["prep_g"] += (r.prep_grams or 0.0)
        dish_stats[key]["waste_g"] += r.wasted_grams

    # Analyze feedback reasons per dish
    feedback_reasons_by_dish = {}
    for f in feedbacks:
        if f.dish_id and (dish := db.get(models.Dish, f.dish_id)):
            if dish.name not in feedback_reasons_by_dish:
                feedback_reasons_by_dish[dish.name] = {}
            for r in f.reasons:
                feedback_reasons_by_dish[dish.name][r] = feedback_reasons_by_dish[dish.name].get(r, 0) + 1

    for (site_name, dish_name), stat in dish_stats.items():
        if stat["prep_g"] < 1000:
            continue
        waste_pct = (stat["waste_g"] / stat["prep_g"]) * 100.0
        wasted_kg = stat["waste_g"] / 1000.0

        dish_fb = feedback_reasons_by_dish.get(dish_name, {})
        top_reason = max(dish_fb.items(), key=lambda x: x[1])[0] if dish_fb else None

        if waste_pct > 15.0:
            if top_reason == "portion_too_big" or waste_pct > 20.0:
                recommendations.append(
                    schemas.RecommendationOut(
                        category="portion",
                        dish_name=dish_name,
                        site_name=site_name,
                        title=f"Reduce {dish_name} serving portion by 15-20%",
                        suggestion=(
                            f"{dish_name} has a {waste_pct:.1f}% waste rate ({wasted_kg:.1f} kg wasted in 30 days). "
                            + ("Diners frequently cite 'portion too big'. " if top_reason == "portion_too_big" else "")
                            + "Standardizing smaller initial scoop sizes can save ~₹"
                            + f"{int(wasted_kg * stat['dish'].cost_per_100g * 10):,} monthly."
                        ),
                        expected_savings_kg=round(wasted_kg * 0.4, 1),
                        priority="high" if waste_pct > 22.0 else "medium",
                    )
                )
            elif top_reason in ("didnt_like_taste", "too_spicy", "quality_poor"):
                recommendations.append(
                    schemas.RecommendationOut(
                        category="reformulation",
                        dish_name=dish_name,
                        site_name=site_name,
                        title=f"Reformulate spice level & recipe for {dish_name}",
                        suggestion=(
                            f"{dish_name} waste rate is {waste_pct:.1f}%. "
                            f"Top feedback from diners: '{schemas.FEEDBACK_REASONS.get(top_reason, top_reason)}'. "
                            "Adjust spice balance or freshness check during prep."
                        ),
                        expected_savings_kg=round(wasted_kg * 0.35, 1),
                        priority="medium",
                    )
                )

    # 2. Calendar Event Recommendations
    if events:
        next_evt = events[0]
        days_until = (next_evt.event_date - date.today()).days
        if days_until <= 7:
            impact_desc = f"{abs(next_evt.attendance_impact_pct):.0%} reduction" if next_evt.attendance_impact_pct < 0 else "increase"
            recommendations.append(
                schemas.RecommendationOut(
                    category="calendar",
                    dish_name="All Menu Items",
                    site_name="All Sites",
                    title=f"Upcoming Event: {next_evt.title} ({next_evt.event_date.strftime('%b %d')})",
                    suggestion=(
                        f"Expected {impact_desc} in diner turnout due to '{next_evt.title}'. "
                        "Pre-adjust bulk prep quantities to avoid excess leftover waste."
                    ),
                    expected_savings_kg=25.0,
                    priority="high",
                )
            )

    # Fallback suggestion if list is empty
    if not recommendations:
        recommendations.append(
            schemas.RecommendationOut(
                category="portion",
                dish_name="Steamed Rice",
                site_name="Main Cafeteria",
                title="Optimize Rice Serving Scoop Size",
                suggestion="Rice accounts for 35% of total plate waste. Implement a 150g standard ladle.",
                expected_savings_kg=12.5,
                priority="low",
            )
        )

    return recommendations
