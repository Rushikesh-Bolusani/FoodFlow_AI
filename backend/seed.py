"""Load realistic demo data so every dashboard has something to say.

Usage (from the repo root):
    venv/Scripts/python.exe -m backend.seed           # add data if missing
    venv/Scripts/python.exe -m backend.seed --reset   # wipe and reseed

Demo story: an education campus with three kitchens and five weeks of
history, where each dish behaves the way real institutional dishes do —
rice always comes back, paneer sits heavy, curd barely does.
"""

import argparse
import random
from datetime import date, timedelta

from sqlalchemy import func

from backend import models
from backend.database import SessionLocal, engine

RNG = random.Random(42)

# ===== SITES =====

SITES = [
    ("Main Cafeteria", "Academic Block"),
    ("Hostel Mess", "Boys Hostel"),
    ("Staff Canteen", "Admin Block"),
]

# ===== DISHES =====
# name, category, kcal/100g, protein/100g, rupees/100g, kg CO2e/100g,
# grams cooked per diner, base share of the dish that comes back

DISHES = [
    ("Steamed Rice", "main", 130, 2.7, 3.0, 0.12, 180, 0.14),
    ("Dal Tadka", "main", 118, 6.0, 5.0, 0.15, 100, 0.08),
    ("Chapati", "main", 240, 7.0, 3.5, 0.20, 90, 0.10),
    ("Mixed Veg Sabzi", "main", 110, 3.0, 6.0, 0.18, 100, 0.13),
    ("Sambar", "main", 65, 3.5, 5.5, 0.14, 90, 0.07),
    ("Paneer Butter Masala", "main", 240, 9.0, 22.0, 0.45, 50, 0.18),
    ("Chicken Curry", "non-veg", 180, 15.0, 28.0, 0.70, 80, 0.06),
    ("Rajma Masala", "main", 140, 6.5, 8.0, 0.20, 80, 0.11),
    ("Plain Curd", "side", 98, 3.5, 10.0, 0.35, 60, 0.05),
    ("Gulab Jamun", "dessert", 300, 4.0, 15.0, 0.30, 45, 0.09),
    ("Poha", "breakfast", 130, 2.5, 3.5, 0.14, 120, 0.06),
    ("Upma", "breakfast", 150, 3.2, 4.0, 0.15, 120, 0.09),
]

MEAL_PLAN = {
    "breakfast": ["Poha", "Upma"],
    "lunch": [
        "Steamed Rice",
        "Dal Tadka",
        "Chapati",
        "Mixed Veg Sabzi",
        "Paneer Butter Masala",
        "Plain Curd",
    ],
    "dinner": [
        "Steamed Rice",
        "Dal Tadka",
        "Chapati",
        "Mixed Veg Sabzi",
        "Rajma Masala",
        "Plain Curd",
    ],
}

# The hostel serves chicken at lunch; the other kitchens are vegetarian.
SITE_EXTRA_DISHES = {"Hostel Mess": {"lunch": ["Chicken Curry"]}}

# ===== BEHAVIOUR =====

# How busy each site is, per meal, on an ordinary weekday.
BASE_ATTENDANCE = {
    "Main Cafeteria": {"breakfast": 180, "lunch": 420, "dinner": 90},
    "Hostel Mess": {"breakfast": 260, "lunch": 380, "dinner": 350},
    "Staff Canteen": {"breakfast": 60, "lunch": 140, "dinner": 20},
}

# Weekends are quiet on campus, but hostel residents stay.
# Keyed by weekday(): 5 = Saturday, 6 = Sunday.
WEEKEND_ATTENDANCE = {
    "Main Cafeteria": {5: 0.55, 6: 0.35},
    "Hostel Mess": {5: 0.95, 6: 0.92},
    "Staff Canteen": {5: 0.30, 6: 0.10},
}

# Hostel diners are fussier; staff are tidy eaters.
SITE_WASTE_MULTIPLIER = {
    "Main Cafeteria": 1.0,
    "Hostel Mess": 1.3,
    "Staff Canteen": 0.7,
}

HISTORY_DAYS = 35


# ===== SEED: CATALOG =====

def seed_catalog(db) -> tuple[dict, dict]:
    """Create sites and dishes if missing. Returns (sites, dishes) by name."""
    sites = {}
    for name, location in SITES:
        site = db.query(models.Site).filter(models.Site.name == name).first()
        if not site:
            site = models.Site(name=name, location=location)
            db.add(site)
            db.flush()
        sites[name] = site

    dishes = {}
    for name, category, kcal, protein, cost, co2e, _, _ in DISHES:
        dish = db.query(models.Dish).filter(models.Dish.name == name).first()
        if not dish:
            dish = models.Dish(
                name=name,
                category=category,
                calories_per_100g=kcal,
                protein_per_100g=protein,
                cost_per_100g=cost,
                co2e_per_100g=co2e,
            )
            db.add(dish)
            db.flush()
        dishes[name] = dish

    db.commit()
    return sites, dishes


# ===== SEED: HISTORY =====

def seed_history(db, sites: dict, dishes: dict) -> tuple[int, int]:
    """Five weeks of attendance + waste records for every site and meal."""
    waste_info = {
        name: (per_diner, base_ratio)
        for name, _, _, _, _, _, per_diner, base_ratio in DISHES
    }

    today = date.today()
    n_attendance = 0
    n_records = 0

    for offset in range(HISTORY_DAYS, 0, -1):
        day = today - timedelta(days=offset)
        weekend = day.weekday() >= 5

        for site_name, site in sites.items():
            for meal, dish_names in MEAL_PLAN.items():
                names = dish_names + SITE_EXTRA_DISHES.get(site_name, {}).get(
                    meal, []
                )

                attendance_factor = WEEKEND_ATTENDANCE[site_name].get(
                    day.weekday(), 1.0
                )
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
    """Seed weekly menu plans, calendar events, and diner QR feedback."""
    # 1. Seed Weekly Menu Plans for all 7 days (0..6)
    n_menu = 0
    for site_name, site in sites.items():
        for dow in range(7):
            for meal, dish_names in MEAL_PLAN.items():
                names = dish_names + SITE_EXTRA_DISHES.get(site_name, {}).get(meal, [])
                for dname in names:
                    if dname in dishes:
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

    # 2. Seed Calendar Events
    today = date.today()
    events = [
        (today + timedelta(days=2), "Mid-Semester Examinations", "exam", -0.35, "Exam period — attendance drops in cafeteria"),
        (today + timedelta(days=8), "Ganesh Chaturthi Holiday", "holiday", -0.70, "Campus holiday — 70% fewer hostel diners"),
        (today + timedelta(days=15), "Annual Cultural Fest", "event", +0.40, "Campus fest — high visitor traffic"),
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

    # 3. Seed Diner Feedback Submissions
    sample_reasons = [
        ["portion_too_big"],
        ["didnt_like_taste"],
        ["portion_too_big", "too_spicy"],
        ["quality_poor"],
        ["not_hungry"],
    ]
    sample_comments = [
        "Portion was too large for lunch.",
        "Gravy was a bit too spicy today.",
        "Loved the paneer, but rice was cold.",
        "Could use smaller initial scoops.",
        "",
    ]

    n_feedback = 0
    main_site = list(sites.values())[0]
    rice_dish = dishes.get("Steamed Rice")
    paneer_dish = dishes.get("Paneer Butter Masala")

    for _ in range(45):
        d_dish = RNG.choice([rice_dish, paneer_dish, None])
        db.add(
            models.Feedback(
                site_id=main_site.id,
                meal=RNG.choice(["lunch", "dinner"]),
                dish_id=d_dish.id if d_dish else None,
                reasons=RNG.choice(sample_reasons),
                comment=RNG.choice(sample_comments),
            )
        )
        n_feedback += 1

    db.commit()
    return n_menu, n_events, n_feedback



# ===== MAIN =====

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the FoodFlow demo database."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="wipe existing data and start fresh",
    )
    args = parser.parse_args()

    if args.reset:
        models.Base.metadata.drop_all(bind=engine)
        print("Existing data wiped.")

    models.Base.metadata.create_all(bind=engine)

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
        print(f"Days of history:   {HISTORY_DAYS}")
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
