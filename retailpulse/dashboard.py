"""
RetailPulse AI — Dashboard data layer.
Fetches live stats from MongoDB for the Gradio dashboard tab.
Falls back to empty/zero values if MongoDB is not connected.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/retailpulse")
DB_NAME = os.getenv("MONGODB_DB_NAME", "retailpulse")

_client = None
_db = None


def _get_db():
    """Lazy MongoDB connection — returns None if unavailable."""
    global _client, _db
    if _db is not None:
        return _db
    try:
        from pymongo import MongoClient
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")
        _db = _client[DB_NAME]
        return _db
    except Exception:
        return None


def get_kpi_cards() -> dict[str, Any]:
    """
    Returns today's KPI summary for the dashboard header cards.
    Returns zeros if MongoDB is unavailable.
    """
    db = _get_db()
    today = str(datetime.now(timezone.utc).date())
    yesterday = str(datetime.now(timezone.utc).date() - timedelta(days=1))

    defaults = {
        "today_revenue": 0.0,
        "today_revenue_change": 0.0,
        "today_footfall": 0,
        "today_footfall_change": 0.0,
        "active_alerts": 0,
        "active_promotions": 0,
        "total_tenants": 0,
    }

    if db is None:
        return defaults

    try:
        # Today's total revenue
        rev_pipeline = [
            {"$match": {"date": today}},
            {"$group": {"_id": None, "total": {"$sum": "$revenue"}}},
        ]
        rev_result = list(db["tenant_revenue"].aggregate(rev_pipeline))
        today_rev = rev_result[0]["total"] if rev_result else 0.0

        # Yesterday's revenue for comparison
        rev_yday = [
            {"$match": {"date": yesterday}},
            {"$group": {"_id": None, "total": {"$sum": "$revenue"}}},
        ]
        yday_result = list(db["tenant_revenue"].aggregate(rev_yday))
        yday_rev = yday_result[0]["total"] if yday_result else 0.0
        rev_change = ((today_rev - yday_rev) / yday_rev * 100) if yday_rev else 0.0

        # Today's footfall
        ff_pipeline = [
            {"$match": {"date": today}},
            {"$group": {"_id": None, "total": {"$sum": "$visitor_count"}}},
        ]
        ff_result = list(db["footfall"].aggregate(ff_pipeline))
        today_ff = ff_result[0]["total"] if ff_result else 0

        # Yesterday's footfall
        ff_yday = [
            {"$match": {"date": yesterday}},
            {"$group": {"_id": None, "total": {"$sum": "$visitor_count"}}},
        ]
        ff_yday_result = list(db["footfall"].aggregate(ff_yday))
        yday_ff = ff_yday_result[0]["total"] if ff_yday_result else 0
        ff_change = ((today_ff - yday_ff) / yday_ff * 100) if yday_ff else 0.0

        return {
            "today_revenue": round(today_rev, 2),
            "today_revenue_change": round(rev_change, 1),
            "today_footfall": today_ff,
            "today_footfall_change": round(ff_change, 1),
            "active_alerts": db["alerts"].count_documents({"resolved": False}),
            "active_promotions": db["promotions"].count_documents({"status": "active"}),
            "total_tenants": db["tenants"].count_documents({"active": True}),
        }
    except Exception:
        return defaults


def get_revenue_chart_data() -> tuple[list, list]:
    """
    Returns (dates, revenues) for the last 14 days revenue trend chart.
    """
    db = _get_db()
    if db is None:
        return [], []

    try:
        today = datetime.now(timezone.utc).date()
        start = str(today - timedelta(days=13))

        pipeline = [
            {"$match": {"date": {"$gte": start}}},
            {"$group": {"_id": "$date", "total": {"$sum": "$revenue"}}},
            {"$sort": {"_id": 1}},
        ]
        results = list(db["tenant_revenue"].aggregate(pipeline))
        dates = [r["_id"] for r in results]
        revenues = [round(r["total"], 2) for r in results]
        return dates, revenues
    except Exception:
        return [], []


def get_footfall_chart_data() -> tuple[list, list]:
    """
    Returns (hours, visitor_counts) for today's hourly footfall chart.
    Falls back to yesterday if today has no data yet.
    """
    db = _get_db()
    if db is None:
        return [], []

    try:
        today = str(datetime.now(timezone.utc).date())
        yesterday = str(datetime.now(timezone.utc).date() - timedelta(days=1))

        for date in [today, yesterday]:
            pipeline = [
                {"$match": {"date": date}},
                {"$group": {"_id": "$hour", "total": {"$sum": "$visitor_count"}}},
                {"$sort": {"_id": 1}},
            ]
            results = list(db["footfall"].aggregate(pipeline))
            if results:
                hours = [f"{r['_id']:02d}:00" for r in results]
                counts = [r["total"] for r in results]
                return hours, counts

        return [], []
    except Exception:
        return [], []


def get_top_tenants_table() -> list[dict]:
    """
    Returns top 10 tenants by revenue this week as a list of dicts.
    """
    db = _get_db()
    if db is None:
        return []

    try:
        today = datetime.now(timezone.utc).date()
        week_start = str(today - timedelta(days=today.weekday()))

        pipeline = [
            {"$match": {"date": {"$gte": week_start}}},
            {
                "$group": {
                    "_id": "$tenant_id",
                    "name": {"$first": "$tenant_name"},
                    "category": {"$first": "$category"},
                    "zone": {"$first": "$zone"},
                    "revenue": {"$sum": "$revenue"},
                    "transactions": {"$sum": "$transactions"},
                }
            },
            {"$sort": {"revenue": -1}},
            {"$limit": 10},
        ]
        results = list(db["tenant_revenue"].aggregate(pipeline))
        return [
            {
                "Tenant": r["name"],
                "Category": r["category"],
                "Zone": r["zone"],
                "Revenue (Week)": f"${r['revenue']:,.0f}",
                "Transactions": r["transactions"],
            }
            for r in results
        ]
    except Exception:
        return []


def get_active_alerts_table() -> list[dict]:
    """
    Returns all unresolved alerts as a list of dicts for the dashboard table.
    """
    db = _get_db()
    if db is None:
        return []

    try:
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts = list(
            db["alerts"]
            .find({"resolved": False}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(20)
        )
        alerts.sort(key=lambda a: severity_order.get(a.get("severity", "LOW"), 4))
        return [
            {
                "Severity": a.get("severity", "—"),
                "Type": a.get("type", "—").replace("_", " ").title(),
                "Tenant/Zone": a.get("tenant_name") or a.get("zone") or "—",
                "Message": a.get("message", "")[:80] + ("…" if len(a.get("message", "")) > 80 else ""),
                "Time": a.get("timestamp", "")[:16].replace("T", " "),
            }
            for a in alerts
        ]
    except Exception:
        return []


def get_category_revenue_data() -> tuple[list, list]:
    """
    Returns (categories, revenues) for this month's revenue by category pie/bar chart.
    """
    db = _get_db()
    if db is None:
        return [], []

    try:
        today = datetime.now(timezone.utc).date()
        month_start = str(today.replace(day=1))

        pipeline = [
            {"$match": {"date": {"$gte": month_start}}},
            {"$group": {"_id": "$category", "total": {"$sum": "$revenue"}}},
            {"$sort": {"total": -1}},
        ]
        results = list(db["tenant_revenue"].aggregate(pipeline))
        categories = [r["_id"] for r in results]
        revenues = [round(r["total"], 2) for r in results]
        return categories, revenues
    except Exception:
        return [], []
