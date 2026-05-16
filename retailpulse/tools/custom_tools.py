"""
Custom Python tools for RetailPulse AI.
These complement the MongoDB MCP tools with utility functions.
"""

from datetime import datetime, timedelta, timezone

def get_date_range(period: str) -> dict:
    """
    Returns start and end ISO date strings for common time periods.

    Args:
        period: One of 'today', 'yesterday', 'this_week', 'last_week',
                'this_month', 'last_month', 'last_7_days', 'last_30_days'

    Returns:
        dict with 'start_date' and 'end_date' as ISO strings (YYYY-MM-DD)
    """
    today = datetime.now(timezone.utc).date()

    if period == "today":
        return {"start_date": str(today), "end_date": str(today)}

    elif period == "yesterday":
        d = today - timedelta(days=1)
        return {"start_date": str(d), "end_date": str(d)}

    elif period == "this_week":
        start = today - timedelta(days=today.weekday())  # Monday
        return {"start_date": str(start), "end_date": str(today)}

    elif period == "last_week":
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return {"start_date": str(start), "end_date": str(end)}

    elif period == "this_month":
        start = today.replace(day=1)
        return {"start_date": str(start), "end_date": str(today)}

    elif period == "last_month":
        first_of_this = today.replace(day=1)
        last_of_prev = first_of_this - timedelta(days=1)
        start = last_of_prev.replace(day=1)
        return {"start_date": str(start), "end_date": str(last_of_prev)}

    elif period == "last_7_days":
        start = today - timedelta(days=7)
        return {"start_date": str(start), "end_date": str(today)}

    elif period == "last_30_days":
        start = today - timedelta(days=30)
        return {"start_date": str(start), "end_date": str(today)}

    else:
        # Default: last 7 days
        start = today - timedelta(days=7)
        return {"start_date": str(start), "end_date": str(today)}


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Formats a number as currency string.

    Args:
        amount: Numeric amount
        currency: Currency code (default USD)

    Returns:
        Formatted string like "$12,345.67"
    """
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}
    symbol = symbols.get(currency, "$")
    return f"{symbol}{amount:,.2f}"


def calculate_percentage_change(current: float, previous: float) -> dict:
    """
    Calculates percentage change between two values.

    Args:
        current: Current period value
        previous: Previous period value

    Returns:
        dict with 'change_pct', 'direction' (up/down/flat), 'indicator' (↑/↓/→)
    """
    if previous == 0:
        return {"change_pct": 0.0, "direction": "flat", "indicator": "→"}

    change = ((current - previous) / abs(previous)) * 100

    if change > 1:
        direction = "up"
        indicator = "↑"
    elif change < -1:
        direction = "down"
        indicator = "↓"
    else:
        direction = "flat"
        indicator = "→"

    return {
        "change_pct": round(change, 1),
        "direction": direction,
        "indicator": indicator,
    }


def generate_report_id(report_type: str) -> str:
    """
    Generates a unique report ID.

    Args:
        report_type: 'daily', 'weekly', 'monthly', 'anomaly', 'promotion'

    Returns:
        String ID like 'RPT-daily-20260516-143022'
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    return f"RPT-{report_type}-{timestamp}"


def generate_promo_id() -> str:
    """
    Generates a unique promotion ID.

    Returns:
        String ID like 'PROMO-20260516-143022'
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    return f"PROMO-{timestamp}"


def generate_alert_id() -> str:
    """
    Generates a unique alert ID.

    Returns:
        String ID like 'ALERT-20260516-143022'
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    return f"ALERT-{timestamp}"


def get_current_timestamp() -> str:
    """
    Returns the current UTC timestamp as an ISO string.

    Returns:
        ISO timestamp string like '2026-05-16T14:30:22Z'
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_day_of_week(date_str: str) -> str:
    """
    Returns the day of week for a given date string.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Day name like 'Monday', 'Saturday', etc.
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%A")
    except ValueError:
        return "Unknown"


def summarize_for_report(data: list, metric_name: str, top_n: int = 5) -> dict:
    """
    Summarizes a list of metric records for inclusion in a report.

    Args:
        data: List of dicts with 'name' and 'value' keys
        metric_name: Human-readable metric name
        top_n: Number of top/bottom performers to include

    Returns:
        Summary dict with top performers, bottom performers, total, average
    """
    if not data:
        return {
            "metric": metric_name,
            "total": 0,
            "average": 0,
            "top_performers": [],
            "bottom_performers": [],
        }

    sorted_data = sorted(data, key=lambda x: x.get("value", 0), reverse=True)
    values = [d.get("value", 0) for d in data]
    total = sum(values)
    average = total / len(values) if values else 0

    return {
        "metric": metric_name,
        "total": round(total, 2),
        "average": round(average, 2),
        "top_performers": sorted_data[:top_n],
        "bottom_performers": sorted_data[-top_n:],
    }
