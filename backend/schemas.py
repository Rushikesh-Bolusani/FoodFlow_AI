"""Pydantic schemas — the shapes the API speaks."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Meal = Literal["breakfast", "lunch", "dinner"]

# Human labels shared by the feedback page, API and dashboards.
FEEDBACK_REASONS = {
    "portion_too_big": "Portion was too big",
    "didnt_like_taste": "Didn't like the taste",
    "quality_poor": "Food wasn't fresh / poor quality",
    "not_hungry": "Just wasn't hungry",
    "too_spicy": "Too spicy",
    "other": "Some other reason",
}


# ---------- Sites ----------

class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str = ""


class SiteIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(default="", max_length=120)


# ---------- Dishes ----------

class DishOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    calories_per_100g: float
    protein_per_100g: float
    cost_per_100g: float
    co2e_per_100g: float
    is_active: bool


class DishIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="main", max_length=60)
    calories_per_100g: float = Field(default=220.0, ge=0)
    protein_per_100g: float = Field(default=8.0, ge=0)
    cost_per_100g: float = Field(default=6.0, ge=0)
    co2e_per_100g: float = Field(default=0.35, ge=0)


# ---------- Waste records ----------

class WasteRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    dish_id: int
    meal: Meal
    record_date: date
    wasted_grams: float
    prep_grams: Optional[float] = None
    source: str
    # Populated by the routers so callers never need a second lookup.
    site_name: str = ""
    dish_name: str = ""


class WasteRecordIn(BaseModel):
    site_id: int
    dish_id: int
    meal: Meal
    wasted_grams: float = Field(gt=0)
    prep_grams: Optional[float] = Field(default=None, gt=0)
    record_date: date = Field(default_factory=date.today)
    source: str = Field(default="manual", max_length=20)


# ---------- Feedback ----------

class FeedbackIn(BaseModel):
    site_id: Optional[int] = None
    meal: Meal = "lunch"
    dish_id: Optional[int] = None
    reasons: list[str] = Field(default_factory=list)
    comment: str = Field(default="", max_length=500)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: Optional[int] = None
    meal: str
    dish_id: Optional[int] = None
    reasons: list[str]
    comment: str
    created_at: datetime
    site_name: str = ""
    dish_name: str = ""


# ---------- Impact & Summary ----------

class ImpactOut(BaseModel):
    total_waste_kg: float
    total_prep_kg: float
    waste_percentage: float
    total_cost_rupees: float
    total_calories_lost: float
    total_protein_kg: float
    total_co2e_kg: float
    days_count: int


# ---------- Benchmarks ----------

class SiteBenchmarkOut(BaseModel):
    site_id: int
    site_name: str
    total_waste_kg: float
    avg_daily_waste_kg: float
    waste_percentage: float
    total_cost_rupees: float
    total_diners: int
    waste_per_diner_grams: float
    top_wasted_dish: str


# ---------- Forecast ----------

class ForecastItem(BaseModel):
    dish_id: int
    dish_name: str
    meal: str
    predicted_attendance: float
    recommended_cook_grams: float
    base_cook_grams: float
    confidence_range_grams: tuple[float, float]
    notes: str = ""


# ---------- Menu Planner & Calendar ----------

class MenuPlanIn(BaseModel):
    site_id: int
    day_of_week: int = Field(ge=0, le=6)
    meal: Meal
    dish_id: int


class MenuPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    day_of_week: int
    meal: str
    dish_id: int
    site_name: str = ""
    dish_name: str = ""
    category: str = ""


class CalendarEventIn(BaseModel):
    event_date: date
    title: str = Field(min_length=1, max_length=120)
    event_type: str = Field(default="holiday", max_length=40)
    attendance_impact_pct: float = Field(default=-0.2)
    notes: str = Field(default="", max_length=255)


class CalendarEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_date: date
    title: str
    event_type: str
    attendance_impact_pct: float
    notes: str


# ---------- Recommendations ----------

class RecommendationOut(BaseModel):
    category: str  # portion / replacement / reformulation / calendar
    dish_name: str
    site_name: str
    title: str
    suggestion: str
    expected_savings_kg: float
    priority: str  # high / medium / low

