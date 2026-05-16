"""
RetailPulse AI — Demo Data Seeder
Populates MongoDB with realistic mall operational data for demonstration.

Usage:
    python scripts/seed_data.py
    python scripts/seed_data.py --reset   # Drop and recreate all collections
"""

import argparse
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/retailpulse")
DB_NAME = os.getenv("MONGODB_DB_NAME", "retailpulse")

# ─────────────────────────────────────────────────────────────────────────────
# Master Data
# ─────────────────────────────────────────────────────────────────────────────
TENANTS = [
    # (tenant_id, name, category, zone, floor, sq_ft, base_daily_revenue)
    ("T001", "Zara", "Fashion", "Zone-A", 1, 3200, 8500),
    ("T002", "H&M", "Fashion", "Zone-A", 1, 2800, 7200),
    ("T003", "Apple Store", "Electronics", "Zone-B", 1, 4500, 22000),
    ("T004", "Samsung Experience", "Electronics", "Zone-B", 1, 3000, 14000),
    ("T005", "Starbucks", "Food & Beverage", "Zone-C", 1, 800, 3200),
    ("T006", "McDonald's", "Food & Beverage", "Zone-C", 1, 1200, 5800),
    ("T007", "Sushi Palace", "Food & Beverage", "Zone-C", 2, 1500, 4200),
    ("T008", "Nike", "Sports", "Zone-D", 2, 2600, 9800),
    ("T009", "Adidas", "Sports", "Zone-D", 2, 2400, 8600),
    ("T010", "Lego Store", "Toys & Games", "Zone-E", 2, 1800, 6400),
    ("T011", "Pandora", "Jewelry", "Zone-F", 1, 600, 4800),
    ("T012", "Swarovski", "Jewelry", "Zone-F", 1, 500, 3900),
    ("T013", "Zara Home", "Home & Living", "Zone-G", 2, 2200, 5200),
    ("T014", "IKEA Mini", "Home & Living", "Zone-G", 2, 3500, 7800),
    ("T015", "Vintage Threads", "Fashion", "Zone-A", 2, 900, 1800),  # underperformer
    ("T016", "TechZone Electronics", "Electronics", "Zone-B", 2, 1100, 2200),  # underperformer
    ("T017", "Artisan Coffee Co", "Food & Beverage", "Zone-C", 2, 400, 1200),  # underperformer
    ("T018", "Foot Locker", "Sports", "Zone-D", 1, 1600, 5400),
    ("T019", "The Body Shop", "Beauty", "Zone-H", 1, 700, 2800),
    ("T020", "Sephora", "Beauty", "Zone-H", 1, 1400, 6200),
]

ZONES = ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F", "Zone-G", "Zone-H"]

# Footfall multipliers by hour (0-23)
HOURLY_FOOTFALL_PATTERN = {
    0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
    6: 0.0, 7: 0.0, 8: 0.0, 9: 0.05, 10: 0.15, 11: 0.35,
    12: 0.65, 13: 0.80, 14: 0.70, 15: 0.75, 16: 0.85, 17: 0.90,
    18: 1.00, 19: 0.95, 20: 0.80, 21: 0.50, 22: 0.10, 23: 0.0,
}

# Day of week multipliers (0=Monday)
DOW_MULTIPLIERS = {0: 0.7, 1: 0.65, 2: 0.7, 3: 0.75, 4: 0.9, 5: 1.0, 6: 0.95}


def connect_db():
    """Connect to MongoDB and return the database."""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print(f"✅ Connected to MongoDB: {MONGODB_URI}")
        return client[DB_NAME]
    except ConnectionFailure as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        print("\nMake sure MongoDB is running. For local dev:")
        print("  docker run -d -p 27017:27017 mongo:7")
        sys.exit(1)


def seed_tenants(db, reset: bool = False):
    """Seed the tenants master collection."""
    col = db["tenants"]
    if reset:
        col.drop()
        print("  Dropped tenants collection")

    if col.count_documents({}) > 0 and not reset:
        print("  ⏭️  Tenants already seeded, skipping")
        return

    today = datetime.now(timezone.utc).date()
    docs = []
    for t in TENANTS:
        tenant_id, name, category, zone, floor, sq_ft, base_rev = t
        # Lease dates: most active, a few expiring soon
        lease_start = today - timedelta(days=random.randint(180, 1800))
        if tenant_id in ("T015", "T016"):  # expiring soon for demo
            lease_end = today + timedelta(days=random.randint(15, 55))
        else:
            lease_end = today + timedelta(days=random.randint(180, 1800))

        docs.append({
            "tenant_id": tenant_id,
            "name": name,
            "category": category,
            "zone": zone,
            "floor": floor,
            "sq_ft": sq_ft,
            "base_daily_revenue": base_rev,
            "lease_start": str(lease_start),
            "lease_end": str(lease_end),
            "contact_email": f"manager@{name.lower().replace(' ', '')}.com",
            "active": True,
        })

    col.insert_many(docs)
    col.create_index("tenant_id", unique=True)
    col.create_index("category")
    col.create_index("zone")
    print(f"  ✅ Seeded {len(docs)} tenants")


def seed_revenue(db, days: int = 90, reset: bool = False):
    """Seed daily tenant revenue for the past N days."""
    col = db["tenant_revenue"]
    if reset:
        col.drop()
        print("  Dropped tenant_revenue collection")

    if col.count_documents({}) > 0 and not reset:
        print("  ⏭️  Revenue already seeded, skipping")
        return

    today = datetime.now(timezone.utc).date()
    docs = []

    for t in TENANTS:
        tenant_id, name, category, zone, floor, sq_ft, base_rev = t

        for day_offset in range(days, 0, -1):
            date = today - timedelta(days=day_offset)
            dow = date.weekday()
            dow_mult = DOW_MULTIPLIERS[dow]

            # Add trend: underperformers declining over last 30 days
            if tenant_id in ("T015", "T016", "T017") and day_offset <= 30:
                trend_factor = 1.0 - (0.015 * (30 - day_offset))  # ~45% decline
            else:
                trend_factor = 1.0

            # Random daily variance ±15%
            variance = random.uniform(0.85, 1.15)
            revenue = base_rev * dow_mult * trend_factor * variance

            # Occasional zero-revenue days (closed, etc.)
            if random.random() < 0.005:
                revenue = 0

            transactions = int(revenue / random.uniform(35, 85))

            docs.append({
                "tenant_id": tenant_id,
                "tenant_name": name,
                "category": category,
                "zone": zone,
                "date": str(date),
                "revenue": round(revenue, 2),
                "transactions": max(0, transactions),
                "avg_transaction_value": round(revenue / max(transactions, 1), 2),
            })

    col.insert_many(docs)
    col.create_index([("tenant_id", ASCENDING), ("date", DESCENDING)])
    col.create_index("date")
    col.create_index("category")
    print(f"  ✅ Seeded {len(docs)} revenue records ({days} days × {len(TENANTS)} tenants)")


def seed_footfall(db, days: int = 90, reset: bool = False):
    """Seed hourly footfall data for the past N days."""
    col = db["footfall"]
    if reset:
        col.drop()
        print("  Dropped footfall collection")

    if col.count_documents({}) > 0 and not reset:
        print("  ⏭️  Footfall already seeded, skipping")
        return

    today = datetime.now(timezone.utc).date()
    docs = []

    # Base hourly visitors per zone
    zone_base_visitors = {
        "Zone-A": 180, "Zone-B": 220, "Zone-C": 350,
        "Zone-D": 160, "Zone-E": 120, "Zone-F": 90,
        "Zone-G": 140, "Zone-H": 130,
    }

    for day_offset in range(days, 0, -1):
        date = today - timedelta(days=day_offset)
        dow = date.weekday()
        dow_mult = DOW_MULTIPLIERS[dow]

        for zone in ZONES:
            base = zone_base_visitors[zone]
            for hour in range(9, 22):  # Mall open 9am-10pm
                hour_mult = HOURLY_FOOTFALL_PATTERN.get(hour, 0)
                variance = random.uniform(0.8, 1.2)

                # Anomaly: Zone-C footfall drop in last 3 days (for demo)
                if zone == "Zone-C" and day_offset <= 3:
                    anomaly_factor = 0.35  # 65% drop — obvious anomaly
                else:
                    anomaly_factor = 1.0

                visitors = int(base * hour_mult * dow_mult * variance * anomaly_factor)
                visitors = max(0, visitors)

                timestamp = datetime.combine(
                    date,
                    datetime.min.time().replace(hour=hour),
                    tzinfo=timezone.utc,
                )

                docs.append({
                    "zone": zone,
                    "date": str(date),
                    "hour": hour,
                    "timestamp": timestamp.isoformat(),
                    "visitor_count": visitors,
                    "day_of_week": date.strftime("%A"),
                })

    col.insert_many(docs)
    col.create_index([("zone", ASCENDING), ("date", DESCENDING)])
    col.create_index("date")
    print(f"  ✅ Seeded {len(docs)} footfall records")


def seed_promotions(db, reset: bool = False):
    """Seed sample promotions."""
    col = db["promotions"]
    if reset:
        col.drop()
        print("  Dropped promotions collection")

    if col.count_documents({}) > 0 and not reset:
        print("  ⏭️  Promotions already seeded, skipping")
        return

    today = datetime.now(timezone.utc).date()

    docs = [
        {
            "promo_id": "PROMO-20260401-001",
            "title": "Spring Fashion Week",
            "tenant_ids": ["T001", "T002", "T015"],
            "category": "Fashion",
            "discount_pct": 25,
            "start_date": str(today - timedelta(days=45)),
            "end_date": str(today - timedelta(days=38)),
            "status": "completed",
            "expected_lift_pct": 30,
            "actual_lift_pct": 28.5,
            "description": "Spring collection launch with 25% off selected items",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "promo_id": "PROMO-20260501-001",
            "title": "Tech Tuesday",
            "tenant_ids": ["T003", "T004", "T016"],
            "category": "Electronics",
            "discount_pct": 15,
            "start_date": str(today - timedelta(days=14)),
            "end_date": str(today + timedelta(days=7)),
            "status": "active",
            "expected_lift_pct": 20,
            "actual_lift_pct": None,
            "description": "Weekly Tuesday tech deals to drive midweek traffic",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "promo_id": "PROMO-20260510-001",
            "title": "Coffee & Snacks Happy Hour",
            "tenant_ids": ["T005", "T017"],
            "category": "Food & Beverage",
            "discount_pct": 20,
            "start_date": str(today - timedelta(days=5)),
            "end_date": str(today + timedelta(days=25)),
            "status": "active",
            "expected_lift_pct": 35,
            "actual_lift_pct": None,
            "description": "2-5pm daily happy hour to boost afternoon footfall",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    col.insert_many(docs)
    col.create_index("promo_id", unique=True)
    col.create_index("status")
    print(f"  ✅ Seeded {len(docs)} promotions")


def seed_alerts(db, reset: bool = False):
    """Seed sample historical alerts."""
    col = db["alerts"]
    if reset:
        col.drop()
        print("  Dropped alerts collection")

    if col.count_documents({}) > 0 and not reset:
        print("  ⏭️  Alerts already seeded, skipping")
        return

    today = datetime.now(timezone.utc).date()

    docs = [
        {
            "alert_id": "ALERT-20260510-001",
            "type": "revenue_drop",
            "severity": "HIGH",
            "tenant_id": "T015",
            "tenant_name": "Vintage Threads",
            "message": "Revenue dropped 42% vs 7-day average. Possible staffing or inventory issue.",
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=6)).isoformat(),
            "resolved": True,
            "resolved_at": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
            "resolution_note": "Restocked key items. Revenue recovering.",
        },
        {
            "alert_id": "ALERT-20260514-001",
            "type": "footfall_drop",
            "severity": "MEDIUM",
            "tenant_id": None,
            "zone": "Zone-C",
            "message": "Zone-C footfall down 65% vs 7-day average. Possible maintenance blockage.",
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "resolved": False,
            "resolved_at": None,
            "resolution_note": None,
        },
        {
            "alert_id": "ALERT-20260515-001",
            "type": "lease_expiry",
            "severity": "MEDIUM",
            "tenant_id": "T016",
            "tenant_name": "TechZone Electronics",
            "message": "Lease expires in 32 days. Renewal negotiation required.",
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "resolved": False,
            "resolved_at": None,
            "resolution_note": None,
        },
    ]

    col.insert_many(docs)
    col.create_index("alert_id", unique=True)
    col.create_index([("resolved", ASCENDING), ("severity", DESCENDING)])
    print(f"  ✅ Seeded {len(docs)} alerts")


def seed_reports(db, reset: bool = False):
    """Seed sample generated reports."""
    col = db["reports"]
    if reset:
        col.drop()
        print("  Dropped reports collection")

    if col.count_documents({}) > 0 and not reset:
        print("  ⏭️  Reports already seeded, skipping")
        return

    today = datetime.now(timezone.utc).date()

    docs = [
        {
            "report_id": "RPT-weekly-20260509-080000",
            "type": "weekly",
            "period_start": str(today - timedelta(days=14)),
            "period_end": str(today - timedelta(days=8)),
            "generated_at": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "summary": (
                "Week of May 5-11: Total mall revenue $1.24M (+3.2% WoW). "
                "Electronics zone led with $312K. Food & Beverage up 8% driven "
                "by Starbucks and McDonald's. Fashion underperforming (-12% WoW). "
                "3 anomalies detected and resolved."
            ),
            "total_revenue": 1240000,
            "total_footfall": 87420,
            "top_performers": [
                {"tenant_id": "T003", "name": "Apple Store", "revenue": 154000},
                {"tenant_id": "T008", "name": "Nike", "revenue": 68600},
                {"tenant_id": "T006", "name": "McDonald's", "revenue": 40600},
            ],
            "underperformers": [
                {"tenant_id": "T015", "name": "Vintage Threads", "revenue": 8400},
                {"tenant_id": "T017", "name": "Artisan Coffee Co", "revenue": 5600},
            ],
        },
    ]

    col.insert_many(docs)
    col.create_index("report_id", unique=True)
    col.create_index([("type", ASCENDING), ("period_end", DESCENDING)])
    print(f"  ✅ Seeded {len(docs)} reports")


def main():
    parser = argparse.ArgumentParser(description="Seed RetailPulse AI demo data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all collections (WARNING: deletes existing data)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days of historical data to generate (default: 90)",
    )
    args = parser.parse_args()

    if args.reset:
        print("⚠️  Reset mode: all existing data will be dropped!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    print(f"\n🌱 Seeding RetailPulse AI demo data ({args.days} days of history)...\n")

    db = connect_db()

    print("📦 Seeding tenants...")
    seed_tenants(db, reset=args.reset)

    print("💰 Seeding revenue data...")
    seed_revenue(db, days=args.days, reset=args.reset)

    print("👣 Seeding footfall data...")
    seed_footfall(db, days=args.days, reset=args.reset)

    print("🎯 Seeding promotions...")
    seed_promotions(db, reset=args.reset)

    print("🚨 Seeding alerts...")
    seed_alerts(db, reset=args.reset)

    print("📊 Seeding reports...")
    seed_reports(db, reset=args.reset)

    print(f"\n✅ Done! Database '{DB_NAME}' is ready for RetailPulse AI.")
    print("\nCollections created:")
    for col_name in db.list_collection_names():
        count = db[col_name].count_documents({})
        print(f"  • {col_name}: {count:,} documents")

    print("\n🚀 Run the agent:")
    print("  python -m retailpulse        # CLI mode")
    print("  python app.py                # Web UI")


if __name__ == "__main__":
    main()
