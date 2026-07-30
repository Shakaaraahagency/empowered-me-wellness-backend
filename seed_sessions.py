"""
seed_sessions.py — Seeds the database with Empowered Me Wellness class sessions.

Run from the backend/ directory:
    python seed_sessions.py

Safe to run multiple times — uses title + start_time as a unique key so it
won't create duplicates if you run it again.
"""

import sys
from datetime import datetime, timezone

from app import create_app
from extensions import db
from models.class_ import Class, Session


# ---------------------------------------------------------------------------
# Class definitions (one Class per category/type)
# ---------------------------------------------------------------------------
CLASSES = [
    {
        "name": "Healing Yoga",
        "description": (
            "An all-level yoga class offering a safe, healing environment for anyone "
            "who wants to reduce stress and improve physical, mental and emotional "
            "well-being."
        ),
        "category": "Kemetic Yoga",
    },
    {
        "name": "Kemetic Yoga",
        "description": (
            "Bring a towel or mat and join us as we relax, restore and rejuvenate. "
            "Increases strength, flexibility, mobility, improves posture, and "
            "increases energy levels."
        ),
        "category": "Kemetic Yoga",
    },
    {
        "name": "Wellness Workshop",
        "description": (
            "Themed wellness sessions covering nutrition, kitchen mindfulness, "
            "and ancestral practices. Recipes and demonstrations included."
        ),
        "category": "Workshop",
    },
    {
        "name": "Zoom Healing & Discussion",
        "description": (
            "Online discussion and healing yoga sessions with Latoya Bridgewater. "
            "Join from anywhere."
        ),
        "category": "Workshop",
    },
]


# ---------------------------------------------------------------------------
# Session data drawn directly from Latoya's class schedule
# ---------------------------------------------------------------------------
# status options: "scheduled" | "closed" | "cancelled"
# location: physical address / platform name
# price: None = free, otherwise set a decimal value e.g. 25.00
# capacity: estimated class size

SESSIONS = [
    # ── Moving Beyond Resilience (Zoom) ──────────────────────────────────────
    {
        "class_name": "Zoom Healing & Discussion",
        "title": "Moving Beyond Resilience",
        "description": (
            "Becoming stronger in places we are broken. A discussion and healing "
            "Yoga Zoom session with Latoya Bridgewater."
        ),
        "start_time": datetime(2021, 5, 21, 18, 0, tzinfo=timezone.utc),
        "end_time": datetime(2021, 5, 21, 19, 30, tzinfo=timezone.utc),
        "location": "Zoom (link sent on registration)",
        "capacity": 50,
        "price": None,
        "status": "closed",
    },

    # ── Wellness in the Kitchen ───────────────────────────────────────────────
    {
        "class_name": "Wellness Workshop",
        "title": "Wellness in the Kitchen",
        "description": (
            "Latoya will give demonstrations and recipes from her e-book "
            "'Nature's Wisdom: Food from the Land' to help boost your immune system. "
            "Register and receive your free copy."
        ),
        "start_time": datetime(2021, 1, 18, 18, 0, tzinfo=timezone.utc),
        "end_time": datetime(2021, 1, 18, 19, 30, tzinfo=timezone.utc),
        "location": "Zoom (link sent on registration)",
        "capacity": 40,
        "price": None,
        "status": "closed",
    },

    # ── Healing Yoga Sessions — May series ───────────────────────────────────
    {
        "class_name": "Healing Yoga",
        "title": "Healing Yoga Sessions with Latoya — May 21",
        "description": (
            "An all-level yoga class offering a safe, healing environment for anyone "
            "who wants to reduce stress & improve physical, mental and emotional "
            "well-being."
        ),
        "start_time": datetime(2021, 5, 21, 18, 0, tzinfo=timezone.utc),
        "end_time": datetime(2021, 5, 21, 19, 0, tzinfo=timezone.utc),
        "location": "Studio — Hamilton, Bermuda",
        "capacity": 12,
        "price": None,
        "status": "closed",
    },
    {
        "class_name": "Healing Yoga",
        "title": "Healing Yoga Sessions with Latoya — May 28",
        "description": (
            "An all-level yoga class offering a safe, healing environment for anyone "
            "who wants to reduce stress & improve physical, mental and emotional "
            "well-being."
        ),
        "start_time": datetime(2021, 5, 28, 18, 0, tzinfo=timezone.utc),
        "end_time": datetime(2021, 5, 28, 19, 0, tzinfo=timezone.utc),
        "location": "Studio — Hamilton, Bermuda",
        "capacity": 12,
        "price": None,
        "status": "closed",
    },
    {
        "class_name": "Healing Yoga",
        "title": "Healing Yoga Sessions with Latoya — June 4",
        "description": (
            "An all-level yoga class offering a safe, healing environment for anyone "
            "who wants to reduce stress & improve physical, mental and emotional "
            "well-being."
        ),
        "start_time": datetime(2021, 6, 4, 18, 0, tzinfo=timezone.utc),
        "end_time": datetime(2021, 6, 4, 19, 0, tzinfo=timezone.utc),
        "location": "Studio — Hamilton, Bermuda",
        "capacity": 12,
        "price": None,
        "status": "closed",
    },
    {
        "class_name": "Healing Yoga",
        "title": "Healing Yoga Sessions with Latoya — June 11",
        "description": (
            "An all-level yoga class offering a safe, healing environment for anyone "
            "who wants to reduce stress & improve physical, mental and emotional "
            "well-being."
        ),
        "start_time": datetime(2021, 6, 11, 18, 0, tzinfo=timezone.utc),
        "end_time": datetime(2021, 6, 11, 19, 0, tzinfo=timezone.utc),
        "location": "Studio — Hamilton, Bermuda",
        "capacity": 12,
        "price": None,
        "status": "closed",
    },

    # ── Kemetic Yoga for Beginners — Jan 2019 ────────────────────────────────
    {
        "class_name": "Kemetic Yoga",
        "title": "Kemetic Yoga for Beginners — 6-Week Series",
        "description": (
            "Bring a towel or a mat and join us as we relax, restore and rejuvenate. "
            "This 6-week yoga series will help you increase strength, flexibility, "
            "mobility, improve posture, increase energy levels."
        ),
        "start_time": datetime(2019, 1, 16, 17, 30, tzinfo=timezone.utc),
        "end_time": datetime(2019, 1, 16, 18, 30, tzinfo=timezone.utc),
        "location": "BIU Multipurpose Room, Bermuda",
        "capacity": 20,
        "price": None,
        "status": "closed",
    },

    # ── Healing Kemetic Yoga — Oct 2018 ──────────────────────────────────────
    {
        "class_name": "Kemetic Yoga",
        "title": "Healing Kemetic Yoga — 6-Week Series",
        "description": (
            "Join us as we refresh, energize, and restore together. This 6-week yoga "
            "series will help restore peace of mind, balance hormonal systems, "
            "increase flexibility and relieve stress."
        ),
        "start_time": datetime(2018, 10, 11, 18, 0, tzinfo=timezone.utc),
        "end_time": datetime(2018, 10, 11, 19, 0, tzinfo=timezone.utc),
        "location": "African Dance Studio, Bermuda",
        "capacity": 20,
        "price": None,
        "status": "closed",
    },

    # ── Kemetic & Restorative Yoga for People of Color — Mar 2018 ────────────
    {
        "class_name": "Kemetic Yoga",
        "title": "Kemetic & Restorative Yoga for People of Color — 6-Week Series",
        "description": (
            "Join us as we revive, restore and connect on the yoga mat. This 6-week "
            "yoga series will help you increase energy levels, strengthen muscles, "
            "improve circulation and deepen your mind-body connection."
        ),
        "start_time": datetime(2018, 3, 7, 18, 30, tzinfo=timezone.utc),
        "end_time": datetime(2018, 3, 7, 19, 30, tzinfo=timezone.utc),
        "location": "Lotus Studio, Bermuda",
        "capacity": 20,
        "price": None,
        "status": "closed",
    },
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------
def seed():
    app = create_app()
    with app.app_context():
        created_classes = 0
        created_sessions = 0
        skipped_sessions = 0

        # 1. Ensure each Class exists
        class_map = {}  # name → Class instance
        for cls_data in CLASSES:
            existing = Class.query.filter_by(name=cls_data["name"]).first()
            if existing:
                class_map[cls_data["name"]] = existing
            else:
                cls = Class(
                    name=cls_data["name"],
                    description=cls_data["description"],
                    category=cls_data["category"],
                    is_active=True,
                )
                db.session.add(cls)
                db.session.flush()  # get the id before committing
                class_map[cls_data["name"]] = cls
                created_classes += 1
                print(f"  [+] Class created: {cls_data['name']}")

        # 2. Insert Sessions (skip if exact title + start_time already exists)
        for s in SESSIONS:
            existing = Session.query.filter_by(
                title=s["title"],
                start_time=s["start_time"],
            ).first()

            if existing:
                print(f"  [~] Skipped (already exists): {s['title']}")
                skipped_sessions += 1
                continue

            cls = class_map.get(s["class_name"])
            session = Session(
                class_id=cls.id if cls else None,
                title=s["title"],
                description=s["description"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                location=s["location"],
                capacity=s["capacity"],
                price=s["price"],
                status=s["status"],
            )
            db.session.add(session)
            created_sessions += 1
            print(f"  [+] Session created: {s['title']}")

        db.session.commit()

        print()
        print("━" * 52)
        print(f"  Classes  : {created_classes} created")
        print(f"  Sessions : {created_sessions} created, {skipped_sessions} skipped")
        print("━" * 52)
        print("  Done. Database seeded successfully.")


if __name__ == "__main__":
    seed()
