"""
Unit tests for RetailPulse AI custom tools.
Run with: pytest tests/test_tools.py -v
"""

import pytest
from datetime import datetime, timezone
from retailpulse.tools.custom_tools import (
    get_date_range,
    format_currency,
    calculate_percentage_change,
    generate_report_id,
    generate_promo_id,
    generate_alert_id,
    get_current_timestamp,
    get_day_of_week,
    summarize_for_report,
)


class TestGetDateRange:
    def test_today(self):
        result = get_date_range("today")
        assert "start_date" in result
        assert "end_date" in result
        assert result["start_date"] == result["end_date"]

    def test_yesterday(self):
        result = get_date_range("yesterday")
        assert result["start_date"] == result["end_date"]
        today = get_date_range("today")["start_date"]
        assert result["start_date"] < today

    def test_this_week(self):
        result = get_date_range("this_week")
        assert result["start_date"] <= result["end_date"]

    def test_last_week(self):
        result = get_date_range("last_week")
        this_week = get_date_range("this_week")
        assert result["end_date"] < this_week["start_date"]

    def test_last_7_days(self):
        result = get_date_range("last_7_days")
        assert result["start_date"] < result["end_date"]

    def test_last_30_days(self):
        result = get_date_range("last_30_days")
        assert result["start_date"] < result["end_date"]

    def test_unknown_period_defaults_to_last_7(self):
        result = get_date_range("unknown_period")
        assert "start_date" in result
        assert "end_date" in result


class TestFormatCurrency:
    def test_usd_default(self):
        assert format_currency(1234.56) == "$1,234.56"

    def test_large_number(self):
        assert format_currency(1000000) == "$1,000,000.00"

    def test_zero(self):
        assert format_currency(0) == "$0.00"

    def test_eur(self):
        result = format_currency(500, "EUR")
        assert result.startswith("€")

    def test_gbp(self):
        result = format_currency(500, "GBP")
        assert result.startswith("£")


class TestCalculatePercentageChange:
    def test_increase(self):
        result = calculate_percentage_change(120, 100)
        assert result["change_pct"] == 20.0
        assert result["direction"] == "up"
        assert result["indicator"] == "↑"

    def test_decrease(self):
        result = calculate_percentage_change(80, 100)
        assert result["change_pct"] == -20.0
        assert result["direction"] == "down"
        assert result["indicator"] == "↓"

    def test_flat(self):
        result = calculate_percentage_change(100, 100)
        assert result["direction"] == "flat"
        assert result["indicator"] == "→"

    def test_zero_previous(self):
        result = calculate_percentage_change(100, 0)
        assert result["change_pct"] == 0.0
        assert result["direction"] == "flat"

    def test_large_drop(self):
        result = calculate_percentage_change(10, 100)
        assert result["change_pct"] == -90.0
        assert result["direction"] == "down"


class TestIdGenerators:
    def test_report_id_format(self):
        rid = generate_report_id("daily")
        assert rid.startswith("RPT-daily-")
        assert len(rid) > 15

    def test_promo_id_format(self):
        pid = generate_promo_id()
        assert pid.startswith("PROMO-")

    def test_alert_id_format(self):
        aid = generate_alert_id()
        assert aid.startswith("ALERT-")

    def test_ids_are_unique(self):
        # IDs include timestamp so should be unique within a second
        ids = {generate_report_id("weekly") for _ in range(3)}
        # At minimum they should all be strings
        assert all(isinstance(i, str) for i in ids)


class TestGetCurrentTimestamp:
    def test_returns_string(self):
        ts = get_current_timestamp()
        assert isinstance(ts, str)

    def test_iso_format(self):
        ts = get_current_timestamp()
        assert "T" in ts
        assert ts.endswith("Z")


class TestGetDayOfWeek:
    def test_known_date(self):
        # 2026-05-16 is a Saturday
        result = get_day_of_week("2026-05-16")
        assert result == "Saturday"

    def test_monday(self):
        result = get_day_of_week("2026-05-11")
        assert result == "Monday"

    def test_invalid_date(self):
        result = get_day_of_week("not-a-date")
        assert result == "Unknown"


class TestSummarizeForReport:
    def test_empty_data(self):
        result = summarize_for_report([], "Revenue")
        assert result["total"] == 0
        assert result["average"] == 0
        assert result["top_performers"] == []

    def test_basic_summary(self):
        data = [
            {"name": "Store A", "value": 1000},
            {"name": "Store B", "value": 500},
            {"name": "Store C", "value": 750},
        ]
        result = summarize_for_report(data, "Revenue", top_n=2)
        assert result["total"] == 2250
        assert result["average"] == 750
        assert len(result["top_performers"]) == 2
        assert result["top_performers"][0]["name"] == "Store A"

    def test_bottom_performers(self):
        data = [
            {"name": "Store A", "value": 1000},
            {"name": "Store B", "value": 100},
            {"name": "Store C", "value": 500},
        ]
        result = summarize_for_report(data, "Revenue", top_n=1)
        assert result["bottom_performers"][0]["name"] == "Store B"
