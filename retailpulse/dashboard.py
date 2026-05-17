"""
RetailPulse AI — Dashboard data layer.
Fetches live stats from MongoDB Atlas for all dashboard tabs.
Falls back gracefully if MongoDB is unavailable.
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
    global _client, _db
    if _db is not None:
        return _db
    try:
        from pymongo import MongoClient
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=4000)
        _client.admin.command("ping")
        _db = _client[DB_NAME]
        return _db
    except Exception:
        return None


def _today() -> str:
    return str(datetime.now(timezone.utc).date())


def _days_ago(n: int) -> str:
    return str(datetime.now(timezone.utc).date() - timedelta(days=n))


# ─────────────────────────────────────────────────────────────────────────────
# KPI Cards
# ─────────────────────────────────────────────────────────────────────────────
def get_kpi_cards() -> dict[str, Any]:
    db = _get_db()
    defaults = {
        "today_revenue": 0.0, "today_revenue_change": 0.0,
        "today_footfall": 0, "today_footfall_change": 0.0,
        "active_alerts": 0, "active_promotions": 0, "total_tenants": 0,
        "week_revenue": 0.0, "week_revenue_change": 0.0,
        "month_revenue": 0.0,
    }
    if db is None:
        return defaults
    try:
        today = _today()
        yesterday = _days_ago(1)
        week_start = _days_ago(7)
        prev_week_start = _days_ago(14)
        month_start = str(datetime.now(timezone.utc).date().replace(day=1))

        def _sum(match):
            r = list(db["tenant_revenue"].aggregate([
                {"$match": match},
                {"$group": {"_id": None, "total": {"$sum": "$revenue"}}}
            ]))
            return r[0]["total"] if r else 0.0

        def _ff_sum(match):
            r = list(db["footfall"].aggregate([
                {"$match": match},
                {"$group": {"_id": None, "total": {"$sum": "$visitor_count"}}}
            ]))
            return r[0]["total"] if r else 0

        today_rev = _sum({"date": today})
        yday_rev = _sum({"date": yesterday})
        week_rev = _sum({"date": {"$gte": week_start, "$lte": today}})
        prev_week_rev = _sum({"date": {"$gte": prev_week_start, "$lt": week_start}})
        month_rev = _sum({"date": {"$gte": month_start, "$lte": today}})
        today_ff = _ff_sum({"date": today})
        yday_ff = _ff_sum({"date": yesterday})

        def _pct(a, b):
            return round((a - b) / b * 100, 1) if b else 0.0

        return {
            "today_revenue": round(today_rev, 2),
            "today_revenue_change": _pct(today_rev, yday_rev),
            "today_footfall": today_ff,
            "today_footfall_change": _pct(today_ff, yday_ff),
            "week_revenue": round(week_rev, 2),
            "week_revenue_change": _pct(week_rev, prev_week_rev),
            "month_revenue": round(month_rev, 2),
            "active_alerts": db["alerts"].count_documents({"resolved": False}),
            "active_promotions": db["promotions"].count_documents({"status": "active"}),
            "total_tenants": db["tenants"].count_documents({"active": True}),
        }
    except Exception:
        return defaults


# ─────────────────────────────────────────────────────────────────────────────
# Revenue Charts
# ─────────────────────────────────────────────────────────────────────────────
def get_revenue_chart_data(days: int = 30) -> tuple[list, list]:
    db = _get_db()
    if db is None:
        return [], []
    try:
        start = _days_ago(days - 1)
        r = list(db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": start}}},
            {"$group": {"_id": "$date", "total": {"$sum": "$revenue"}}},
            {"$sort": {"_id": 1}},
        ]))
        return [x["_id"] for x in r], [round(x["total"], 2) for x in r]
    except Exception:
        return [], []


def get_revenue_by_category_trend(days: int = 30) -> dict[str, tuple[list, list]]:
    """Returns per-category revenue trend for the last N days."""
    db = _get_db()
    if db is None:
        return {}
    try:
        start = _days_ago(days - 1)
        r = list(db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": start}}},
            {"$group": {"_id": {"cat": "$category", "date": "$date"},
                        "total": {"$sum": "$revenue"}}},
            {"$sort": {"_id.date": 1}},
        ]))
        result: dict = {}
        for row in r:
            cat = row["_id"]["cat"]
            date = row["_id"]["date"]
            if cat not in result:
                result[cat] = ([], [])
            result[cat][0].append(date)
            result[cat][1].append(round(row["total"], 2))
        return result
    except Exception:
        return {}


def get_zone_revenue_data() -> tuple[list, list]:
    """Returns (zones, revenues) for this month."""
    db = _get_db()
    if db is None:
        return [], []
    try:
        month_start = str(datetime.now(timezone.utc).date().replace(day=1))
        r = list(db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": month_start}}},
            {"$group": {"_id": "$zone", "total": {"$sum": "$revenue"}}},
            {"$sort": {"total": -1}},
        ]))
        return [x["_id"] for x in r], [round(x["total"], 2) for x in r]
    except Exception:
        return [], []


# ─────────────────────────────────────────────────────────────────────────────
# Footfall Charts
# ─────────────────────────────────────────────────────────────────────────────
def get_footfall_chart_data() -> tuple[list, list]:
    db = _get_db()
    if db is None:
        return [], []
    try:
        for date in [_today(), _days_ago(1)]:
            r = list(db["footfall"].aggregate([
                {"$match": {"date": date}},
                {"$group": {"_id": "$hour", "total": {"$sum": "$visitor_count"}}},
                {"$sort": {"_id": 1}},
            ]))
            if r:
                return [f"{x['_id']:02d}:00" for x in r], [x["total"] for x in r]
        return [], []
    except Exception:
        return [], []


def get_footfall_heatmap_data() -> tuple[list, list, list]:
    """Returns (zones, hours, matrix) for a footfall heatmap."""
    db = _get_db()
    if db is None:
        return [], [], []
    try:
        start = _days_ago(6)
        r = list(db["footfall"].aggregate([
            {"$match": {"date": {"$gte": start}}},
            {"$group": {"_id": {"zone": "$zone", "hour": "$hour"},
                        "avg": {"$avg": "$visitor_count"}}},
        ]))
        zones_set = sorted(set(x["_id"]["zone"] for x in r))
        hours_set = sorted(set(x["_id"]["hour"] for x in r))
        lookup = {(x["_id"]["zone"], x["_id"]["hour"]): x["avg"] for x in r}
        matrix = [[round(lookup.get((z, h), 0)) for h in hours_set]
                  for z in zones_set]
        return zones_set, [f"{h:02d}:00" for h in hours_set], matrix
    except Exception:
        return [], [], []


def get_weekly_footfall_trend() -> tuple[list, list]:
    """Returns (dates, total_visitors) for last 14 days."""
    db = _get_db()
    if db is None:
        return [], []
    try:
        start = _days_ago(13)
        r = list(db["footfall"].aggregate([
            {"$match": {"date": {"$gte": start}}},
            {"$group": {"_id": "$date", "total": {"$sum": "$visitor_count"}}},
            {"$sort": {"_id": 1}},
        ]))
        return [x["_id"] for x in r], [x["total"] for x in r]
    except Exception:
        return [], []


# ─────────────────────────────────────────────────────────────────────────────
# Tenant Tables
# ─────────────────────────────────────────────────────────────────────────────
def get_top_tenants_table(limit: int = 10) -> list[dict]:
    db = _get_db()
    if db is None:
        return []
    try:
        week_start = _days_ago(6)
        prev_week_start = _days_ago(13)

        # This week
        this_week = {x["_id"]: x for x in db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": week_start}}},
            {"$group": {"_id": "$tenant_id", "name": {"$first": "$tenant_name"},
                        "category": {"$first": "$category"}, "zone": {"$first": "$zone"},
                        "revenue": {"$sum": "$revenue"}, "txns": {"$sum": "$transactions"}}},
        ])}
        # Prev week
        prev_week = {x["_id"]: x["revenue"] for x in db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": prev_week_start, "$lt": week_start}}},
            {"$group": {"_id": "$tenant_id", "revenue": {"$sum": "$revenue"}}},
        ])}

        rows = []
        for tid, d in this_week.items():
            prev = prev_week.get(tid, 0)
            chg = round((d["revenue"] - prev) / prev * 100, 1) if prev else 0.0
            arrow = "↑" if chg > 0 else ("↓" if chg < 0 else "→")
            rows.append({
                "Tenant": d["name"],
                "Category": d["category"],
                "Zone": d["zone"],
                "Revenue (Week)": f"${d['revenue']:,.0f}",
                "vs Last Week": f"{arrow} {abs(chg):.1f}%",
                "Transactions": d["txns"],
            })
        rows.sort(key=lambda x: float(x["Revenue (Week)"].replace("$","").replace(",","")), reverse=True)
        return rows[:limit]
    except Exception:
        return []


def get_underperformers_table() -> list[dict]:
    """Returns tenants with >15% revenue decline vs prior week."""
    db = _get_db()
    if db is None:
        return []
    try:
        week_start = _days_ago(6)
        prev_week_start = _days_ago(13)

        this_week = {x["_id"]: x for x in db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": week_start}}},
            {"$group": {"_id": "$tenant_id", "name": {"$first": "$tenant_name"},
                        "category": {"$first": "$category"}, "zone": {"$first": "$zone"},
                        "revenue": {"$sum": "$revenue"}}},
        ])}
        prev_week = {x["_id"]: x["revenue"] for x in db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": prev_week_start, "$lt": week_start}}},
            {"$group": {"_id": "$tenant_id", "revenue": {"$sum": "$revenue"}}},
        ])}

        rows = []
        for tid, d in this_week.items():
            prev = prev_week.get(tid, 0)
            if prev > 0:
                chg = (d["revenue"] - prev) / prev * 100
                if chg < -15:
                    rows.append({
                        "Tenant": d["name"],
                        "Category": d["category"],
                        "Zone": d["zone"],
                        "This Week": f"${d['revenue']:,.0f}",
                        "Last Week": f"${prev:,.0f}",
                        "Decline": f"↓ {abs(chg):.1f}%",
                    })
        rows.sort(key=lambda x: float(x["Decline"].replace("↓ ","").replace("%","")), reverse=True)
        return rows
    except Exception:
        return []


def get_lease_expiry_table() -> list[dict]:
    """Returns tenants with leases expiring within 90 days."""
    db = _get_db()
    if db is None:
        return []
    try:
        today = _today()
        in_90 = _days_ago(-90)  # future date
        tenants = list(db["tenants"].find(
            {"lease_end": {"$gte": today, "$lte": in_90}, "active": True},
            {"_id": 0, "tenant_id": 1, "name": 1, "category": 1, "zone": 1, "lease_end": 1}
        ).sort("lease_end", 1).limit(20))

        rows = []
        for t in tenants:
            from datetime import date
            end = datetime.strptime(t["lease_end"], "%Y-%m-%d").date()
            days_left = (end - datetime.now(timezone.utc).date()).days
            urgency = "🔴 URGENT" if days_left <= 30 else ("🟡 Soon" if days_left <= 60 else "🟢 OK")
            rows.append({
                "Tenant": t["name"],
                "Category": t["category"],
                "Zone": t["zone"],
                "Lease Ends": t["lease_end"],
                "Days Left": days_left,
                "Status": urgency,
            })
        return rows
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Alerts & Promotions
# ─────────────────────────────────────────────────────────────────────────────
def get_active_alerts_table() -> list[dict]:
    db = _get_db()
    if db is None:
        return []
    try:
        sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        alerts = list(db["alerts"].find({"resolved": False}, {"_id": 0})
                      .sort("timestamp", -1).limit(20))
        alerts.sort(key=lambda a: sev_order.get(a.get("severity", "LOW"), 4))
        return [{
            "Severity": a.get("severity", "—"),
            "Type": a.get("type", "—").replace("_", " ").title(),
            "Tenant/Zone": a.get("tenant_name") or a.get("zone") or "—",
            "Message": (a.get("message", "")[:70] + "…"
                        if len(a.get("message", "")) > 70 else a.get("message", "")),
            "Time": a.get("timestamp", "")[:16].replace("T", " "),
        } for a in alerts]
    except Exception:
        return []


def get_promotions_table() -> list[dict]:
    """Returns all active and upcoming promotions."""
    db = _get_db()
    if db is None:
        return []
    try:
        promos = list(db["promotions"].find(
            {"status": {"$in": ["active", "planned"]}}, {"_id": 0}
        ).sort("start_date", -1).limit(20))
        return [{
            "Title": p.get("title", "—"),
            "Category": p.get("category", "—"),
            "Discount": f"{p.get('discount_pct', 0)}%",
            "Start": p.get("start_date", "—"),
            "End": p.get("end_date", "—"),
            "Expected Lift": f"+{p.get('expected_lift_pct', 0)}%",
            "Status": p.get("status", "—").upper(),
        } for p in promos]
    except Exception:
        return []


def get_category_revenue_data() -> tuple[list, list]:
    db = _get_db()
    if db is None:
        return [], []
    try:
        month_start = str(datetime.now(timezone.utc).date().replace(day=1))
        r = list(db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": month_start}}},
            {"$group": {"_id": "$category", "total": {"$sum": "$revenue"}}},
            {"$sort": {"total": -1}},
        ]))
        return [x["_id"] for x in r], [round(x["total"], 2) for x in r]
    except Exception:
        return [], []


def get_summary_stats() -> dict:
    """Returns high-level stats for the summary bar."""
    db = _get_db()
    if db is None:
        return {}
    try:
        month_start = str(datetime.now(timezone.utc).date().replace(day=1))
        total_rev = list(db["tenant_revenue"].aggregate([
            {"$match": {"date": {"$gte": month_start}}},
            {"$group": {"_id": None, "total": {"$sum": "$revenue"},
                        "txns": {"$sum": "$transactions"}}}
        ]))
        rev = total_rev[0]["total"] if total_rev else 0
        txns = total_rev[0]["txns"] if total_rev else 0
        return {
            "month_revenue": round(rev, 2),
            "month_transactions": txns,
            "avg_transaction": round(rev / txns, 2) if txns else 0,
            "active_tenants": db["tenants"].count_documents({"active": True}),
            "open_alerts": db["alerts"].count_documents({"resolved": False}),
            "active_promos": db["promotions"].count_documents({"status": "active"}),
        }
    except Exception:
        return {}
