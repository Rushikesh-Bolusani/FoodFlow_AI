"""Load South Indian institutional-kitchen demo data.

Usage (from the repo root):
    venv/Scripts/python.exe -m backend.seed
    venv/Scripts/python.exe -m backend.seed --reset
"""

import argparse
import random
from datetime import date, timedelta

from sqlalchemy import func

from backend import models
from backend.database import SessionLocal, engine, migrate_sqlite

RNG = random.Random(42)

# ===== SITES =====

SITES = [
    ("Hostel 1", "Hostel Block 1 Mess"),
]

# name, category, kcal/100g, protein/100g, rupees/100g, kg CO2e/100g,
# grams cooked per diner, base leftover share, cv_class
DISHES = [
    ("Steamed Rice", "main", 130, 2.7, 3.0, 0.12, 180, 0.16, "rice"),
    ("Sambar Rice", "main", 110, 3.4, 5.5, 0.14, 160, 0.11, "sambar_rice"),
    ("Curd Rice", "main", 120, 3.2, 6.0, 0.20, 140, 0.08, "curd_rice"),
    ("Chicken Biryani", "non-veg", 190, 9.0, 18.0, 0.55, 200, 0.10, "biryani"),
    ("Rasam", "side", 35, 1.2, 3.5, 0.08, 80, 0.07, "rasam"),
    ("Vegetable Curry", "main", 95, 2.8, 6.5, 0.16, 100, 0.14, "curry"),
    ("Potato Curry", "main", 120, 2.2, 5.0, 0.14, 90, 0.13, "potato_curry"),
    ("Green Vegetable Curry", "main", 85, 3.0, 6.0, 0.15, 90, 0.12, "green_curry"),
    ("Chicken Curry", "non-veg", 180, 15.0, 28.0, 0.70, 90, 0.07, "chicken"),
    ("Boiled Egg", "side", 155, 13.0, 8.0, 0.25, 50, 0.05, "egg"),
    ("Fresh Salad", "side", 40, 1.5, 4.0, 0.08, 60, 0.09, "salad"),
    ("Bonda", "snack", 260, 5.0, 8.0, 0.22, 80, 0.08, "bonda"),
    ("Banana Chips", "snack", 520, 2.5, 12.0, 0.18, 30, 0.04, "chips"),
    ("Sweet", "dessert", 280, 3.5, 12.0, 0.28, 50, 0.09, "sweet"),
]

# Day-of-week menus (0=Monday). Only dishes the detector can name.
WEEKLY_MENU = {
    0: {  # Monday
        "breakfast": ["Boiled Egg", "Bonda", "Steamed Rice"],
        "lunch": ["Steamed Rice", "Sambar Rice", "Rasam", "Vegetable Curry", "Curd Rice", "Fresh Salad"],
        "snacks": ["Bonda", "Banana Chips"],
        "dinner": ["Steamed Rice", "Sambar Rice", "Potato Curry", "Curd Rice", "Sweet"],
    },
    1: {
        "breakfast": ["Boiled Egg", "Bonda"],
        "lunch": ["Steamed Rice", "Sambar Rice", "Rasam", "Chicken Curry", "Curd Rice", "Fresh Salad"],
        "snacks": ["Banana Chips"],
        "dinner": ["Steamed Rice", "Green Vegetable Curry", "Curd Rice", "Sweet"],
    },
    2: {
        "breakfast": ["Boiled Egg", "Steamed Rice"],
        "lunch": ["Chicken Biryani", "Curd Rice", "Fresh Salad", "Rasam"],
        "snacks": ["Bonda"],
        "dinner": ["Steamed Rice", "Sambar Rice", "Vegetable Curry", "Curd Rice"],
    },
    3: {
        "breakfast": ["Bonda", "Boiled Egg"],
        "lunch": ["Steamed Rice", "Sambar Rice", "Potato Curry", "Rasam", "Curd Rice", "Fresh Salad"],
        "snacks": ["Bonda", "Banana Chips"],
        "dinner": ["Steamed Rice", "Chicken Curry", "Green Vegetable Curry", "Curd Rice"],
    },
    4: {
        "breakfast": ["Boiled Egg", "Bonda", "Steamed Rice"],
        "lunch": ["Steamed Rice", "Sambar Rice", "Chicken Curry", "Rasam", "Curd Rice", "Fresh Salad"],
        "snacks": ["Banana Chips"],
        "dinner": ["Steamed Rice", "Vegetable Curry", "Curd Rice", "Sweet"],
    },
    5: {
        "breakfast": ["Boiled Egg", "Bonda"],
        "lunch": ["Chicken Biryani", "Curd Rice", "Fresh Salad"],
        "snacks": ["Bonda"],
        "dinner": ["Steamed Rice", "Sambar Rice", "Potato Curry", "Curd Rice"],
    },
    6: {
        "breakfast": ["Boiled Egg", "Steamed Rice"],
        "lunch": ["Steamed Rice", "Sambar Rice", "Vegetable Curry", "Rasam", "Curd Rice"],
        "snacks": ["Banana Chips"],
        "dinner": ["Steamed Rice", "Green Vegetable Curry", "Curd Rice", "Sweet"],
    },
}

BASE_ATTENDANCE = {
    "Hostel 1": {"breakfast": 250, "lunch": 450, "snacks": 200, "dinner": 380},
}

WEEKEND_ATTENDANCE = {
    "Hostel 1": {5: 0.60, 6: 0.40},
}

SITE_WASTE_MULTIPLIER = {
    "Hostel 1": 1.0,
}

HISTORY_DAYS = 35


def dishes_for_day(dow: int, meal: str) -> list[str]:
    return list(WEEKLY_MENU[dow][meal])


def seed_catalog(db) -> tuple[dict, dict]:
    sites = {}
    for name, location in SITES:
        site = db.query(models.Site).filter(models.Site.name == name).first()
        if not site:
            site = models.Site(name=name, location=location)
            db.add(site)
            db.flush()
        sites[name] = site

    dishes = {}
    for name, category, kcal, protein, cost, co2e, _, _, cv_class in DISHES:
        dish = db.query(models.Dish).filter(models.Dish.name == name).first()
        if not dish:
            dish = models.Dish(
                name=name,
                category=category,
                calories_per_100g=kcal,
                protein_per_100g=protein,
                cost_per_100g=cost,
                co2e_per_100g=co2e,
                cv_class=cv_class,
            )
            db.add(dish)
            db.flush()
        else:
            dish.cv_class = cv_class
            dish.category = category
        dishes[name] = dish

    db.commit()
    return sites, dishes


def seed_history(db, sites: dict, dishes: dict) -> tuple[int, int]:
    waste_info = {
        name: (per_diner, base_ratio)
        for name, _, _, _, _, _, per_diner, base_ratio, _ in DISHES
    }

    today = date.today()
    n_attendance = 0
    n_records = 0

    for offset in range(HISTORY_DAYS, -1, -1):
        day = today - timedelta(days=offset)
        weekend = day.weekday() >= 5
        dow = day.weekday()

        for site_name, site in sites.items():
            for meal in ("breakfast", "lunch", "snacks", "dinner"):
                names = dishes_for_day(dow, meal)
                attendance_factor = WEEKEND_ATTENDANCE[site_name].get(day.weekday(), 1.0)
                headcount = BASE_ATTENDANCE[site_name][meal] * attendance_factor
                headcount *= RNG.uniform(0.92, 1.08)
                headcount = int(round(headcount))

                db.add(
                    models.Attendance(
                        site_id=site.id,
                        meal=meal,
                        day=day,
                        headcount=headcount,
                    )
                )
                n_attendance += 1

                for name in names:
                    per_diner, base_ratio = waste_info[name]
                    prep = per_diner * headcount * RNG.uniform(1.05, 1.15)
                    ratio = base_ratio * SITE_WASTE_MULTIPLIER[site_name]
                    ratio *= RNG.uniform(0.7, 1.3)
                    if weekend:
                        ratio *= 1.1
                    ratio = min(max(ratio, 0.02), 0.45)
                    db.add(
                        models.WasteRecord(
                            site_id=site.id,
                            dish_id=dishes[name].id,
                            meal=meal,
                            record_date=day,
                            prep_grams=round(prep / 10) * 10,
                            wasted_grams=round(prep * ratio / 10) * 10,
                            source="seed",
                        )
                    )
                    n_records += 1

    db.commit()
    return n_attendance, n_records


def seed_menu_and_calendar(db, sites: dict, dishes: dict) -> tuple[int, int, int]:
    n_menu = 0
    for site in sites.values():
        for dow, meals in WEEKLY_MENU.items():
            for meal, names in meals.items():
                for dname in names:
                    db.add(
                        models.MenuPlan(
                            site_id=site.id,
                            day_of_week=dow,
                            meal=meal,
                            dish_id=dishes[dname].id,
                            is_active=True,
                        )
                    )
                    n_menu += 1

    today = date.today()
    events = [
        (today + timedelta(days=2), "Mid-Semester Examinations", "exam", -0.35, "Exam days — fewer cafeteria diners"),
        (today + timedelta(days=8), "Regional Holiday", "holiday", -0.70, "Campus holiday — kitchens cook for residents only"),
        (today + timedelta(days=15), "Annual Cultural Fest", "event", +0.40, "Visitor traffic — extra lunch and snacks"),
    ]
    n_events = 0
    for evt_date, title, etype, impact, notes in events:
        db.add(
            models.CalendarEvent(
                event_date=evt_date,
                title=title,
                event_type=etype,
                attendance_impact_pct=impact,
                notes=notes,
            )
        )
        n_events += 1

    sample_reasons = [
        ["portion_too_big"],
        ["didnt_like_taste"],
        ["portion_too_big", "too_spicy"],
        ["quality_poor"],
        ["not_hungry"],
    ]
    sample_comments = [
        "Rice portion was too large for lunch.",
        "Sambar was a bit too spicy today.",
        "Loved the biryani; curd rice was cold.",
        "Please use a smaller first scoop of rice.",
        "",
    ]

    n_feedback = 0
    main_site = list(sites.values())[0]
    rice = dishes.get("Steamed Rice")
    biryani = dishes.get("Chicken Biryani")
    sambar = dishes.get("Sambar Rice")

    for _ in range(45):
        d_dish = RNG.choice([rice, biryani, sambar, None])
        db.add(
            models.Feedback(
                site_id=main_site.id,
                meal=RNG.choice(["lunch", "dinner", "snacks"]),
                dish_id=d_dish.id if d_dish else None,
                reasons=RNG.choice(sample_reasons),
                rating=RNG.choice([2, 3, 3, 4, 4, 5]),
                comment=RNG.choice(sample_comments),
            )
        )
        n_feedback += 1

    db.commit()
    return n_menu, n_events, n_feedback


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the FoodFlow demo database.")
    parser.add_argument("--reset", action="store_true", help="wipe existing data and start fresh")
    args = parser.parse_args()

    if args.reset:
        models.Base.metadata.drop_all(bind=engine)
        print("Existing data wiped.")

    models.Base.metadata.create_all(bind=engine)
    migrate_sqlite()

    db = SessionLocal()
    try:
        already = db.query(models.WasteRecord).count()
        if already and not args.reset:
            print(
                f"Demo data already present ({already} waste records). "
                "Use --reset to start fresh."
            )
            return

        sites, dishes = seed_catalog(db)
        n_attendance, n_records = seed_history(db, sites, dishes)
        n_menu, n_events, n_feedback = seed_menu_and_calendar(db, sites, dishes)

        total_waste_kg = (
            db.query(func.sum(models.WasteRecord.wasted_grams)).scalar() or 0
        ) / 1000

        print()
        print("================================")
        print("DEMO DATA READY")
        print("================================")
        print(f"Sites:            {len(sites)}")
        print(f"Dishes:           {len(dishes)}")
        print(f"Days of history:   {HISTORY_DAYS + 1} (includes today)")
        print(f"Attendance rows:   {n_attendance}")
        print(f"Waste records:    {n_records}")
        print(f"Menu plan items:  {n_menu}")
        print(f"Calendar events:  {n_events}")
        print(f"Feedback entries: {n_feedback}")
        print(f"Total wasted:     {total_waste_kg:,.0f} kg")
        print()
        print("Start the API with:")
        print("  venv/Scripts/python.exe -m uvicorn backend.main:app --reload")
    finally:
        db.close()


if __name__ == "__main__":
    main()
