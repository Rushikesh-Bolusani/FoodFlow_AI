"""Database models for FoodFlow AI.

The waste record is the heart of the system: every row captures one dish at
one meal at one site, how much was cooked, and how much came back. Around it
sit the reference data (sites, dishes with their nutrition/cost figures),
attendance (forecast input) and diner feedback (the "why").
"""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Site(Base):
    """A kitchen / cafeteria where waste is tracked."""

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    location: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    waste_records: Mapped[list["WasteRecord"]] = relationship(
        back_populates="site"
    )


class Dish(Base):
    """A dish on the menu, with per-100g figures used for impact conversion."""

    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(60), default="main")
    # All figures are per 100 g of the dish as served.
    calories_per_100g: Mapped[float] = mapped_column(Float, default=220.0)
    protein_per_100g: Mapped[float] = mapped_column(Float, default=8.0)
    cost_per_100g: Mapped[float] = mapped_column(Float, default=6.0)  # rupees
    co2e_per_100g: Mapped[float] = mapped_column(Float, default=0.35)  # kg CO2e
    cv_class: Mapped[str] = mapped_column(String(60), default="")
    is_active: Mapped[bool] = mapped_column(default=True)

    waste_records: Mapped[list["WasteRecord"]] = relationship(
        back_populates="dish"
    )


class WasteRecord(Base):
    """How much of one dish came back at one meal, and how much was cooked."""

    __tablename__ = "waste_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"), index=True)
    meal: Mapped[str] = mapped_column(String(20))  # breakfast / lunch / snacks / dinner
    record_date: Mapped[date] = mapped_column(Date, index=True)
    wasted_grams: Mapped[float] = mapped_column(Float)
    prep_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    site: Mapped["Site"] = relationship(back_populates="waste_records")
    dish: Mapped["Dish"] = relationship(back_populates="waste_records")


class Attendance(Base):
    """How many people actually ate at a site/meal/day — forecast input."""

    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("site_id", "meal", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    meal: Mapped[str] = mapped_column(String(20))
    day: Mapped[date] = mapped_column(Date, index=True)
    headcount: Mapped[float]


class Feedback(Base):
    """One diner's answer to 'why did you leave food?' via the QR code."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int | None] = mapped_column(
        ForeignKey("sites.id"), nullable=True, index=True
    )
    meal: Mapped[str] = mapped_column(String(20))
    dish_id: Mapped[int | None] = mapped_column(
        ForeignKey("dishes.id"), nullable=True
    )
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class MenuPlan(Base):
    """Weekly scheduled dishes per site, meal and day of week (0=Mon, 6=Sun)."""

    __tablename__ = "menu_plans"
    __table_args__ = (
        UniqueConstraint("site_id", "day_of_week", "meal", "dish_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    day_of_week: Mapped[int] = mapped_column(index=True)  # 0=Monday, 6=Sunday
    meal: Mapped[str] = mapped_column(String(20))
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    site: Mapped["Site"] = relationship()
    dish: Mapped["Dish"] = relationship()


class CalendarEvent(Base):
    """Holidays, exams, and special events affecting kitchen attendance."""

    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(40), default="holiday")  # holiday/exam/event
    attendance_impact_pct: Mapped[float] = mapped_column(Float, default=-0.2)  # e.g., -0.3 for 30% fewer diners
    notes: Mapped[str] = mapped_column(String(255), default="")

