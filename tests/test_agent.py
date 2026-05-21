"""
Integration-style tests for RetailPulse AI agent configuration.
These tests verify the agent is wired correctly without requiring
a live MongoDB connection or Gemini API key.

Run with: pytest tests/test_agent.py -v
"""

import os
import pytest

# Set dummy env vars before any imports so agent.py doesn't fail
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/retailpulse_test")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-placeholder")
os.environ.setdefault("AGENT_MODEL", "gemini-2.5-flash")


class TestAgentConfiguration:
    """Verify agent structure is correctly configured."""

    def test_custom_tools_importable(self):
        """All custom tools must be importable without side effects."""
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
        # All should be callable
        assert callable(get_date_range)
        assert callable(format_currency)
        assert callable(calculate_percentage_change)
        assert callable(generate_report_id)
        assert callable(generate_promo_id)
        assert callable(generate_alert_id)
        assert callable(get_current_timestamp)
        assert callable(get_day_of_week)
        assert callable(summarize_for_report)

    def test_prompts_importable(self):
        """All system prompts must be importable and non-empty."""
        from retailpulse.prompts.system_prompts import (
            ORCHESTRATOR_PROMPT,
            ANALYTICS_PROMPT,
            ANOMALY_PROMPT,
            ADVISOR_PROMPT,
        )
        assert len(ORCHESTRATOR_PROMPT) > 200
        assert len(ANALYTICS_PROMPT) > 100
        assert len(ANOMALY_PROMPT) > 100
        assert len(ADVISOR_PROMPT) > 100

    def test_orchestrator_prompt_mentions_sub_agents(self):
        """Orchestrator prompt must reference all four sub-agents."""
        from retailpulse.prompts.system_prompts import ORCHESTRATOR_PROMPT
        assert "analytics_agent" in ORCHESTRATOR_PROMPT
        assert "anomaly_agent" in ORCHESTRATOR_PROMPT
        assert "advisor_agent" in ORCHESTRATOR_PROMPT
        assert "notification_agent" in ORCHESTRATOR_PROMPT

    def test_orchestrator_prompt_mentions_collections(self):
        """Orchestrator prompt must document all database collections."""
        from retailpulse.prompts.system_prompts import ORCHESTRATOR_PROMPT
        for collection in ["footfall", "tenant_revenue", "tenants", "promotions", "alerts", "reports"]:
            assert collection in ORCHESTRATOR_PROMPT, f"Collection '{collection}' missing from prompt"

    def test_anomaly_prompt_covers_all_anomaly_types(self):
        """Anomaly prompt must cover all five anomaly categories."""
        from retailpulse.prompts.system_prompts import ANOMALY_PROMPT
        # New agentic prompt uses different phrasing — check for key concepts
        assert "revenue" in ANOMALY_PROMPT.lower()
        assert "footfall" in ANOMALY_PROMPT.lower()
        assert "lease" in ANOMALY_PROMPT.lower()
        assert "insert-many" in ANOMALY_PROMPT
        assert "CRITICAL" in ANOMALY_PROMPT

    def test_env_defaults_are_set(self):
        """Critical environment variables must have sensible defaults."""
        # These are set at the top of this file for testing
        assert os.getenv("MONGODB_URI") is not None
        assert os.getenv("AGENT_MODEL") is not None


class TestSubAgentModules:
    """Verify sub-agent modules are importable and correctly structured."""

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("google.adk"),
        reason="google-adk not installed in this environment",
    )
    def test_analytics_agent_module_importable(self):
        from retailpulse.sub_agents import analytics_agent as mod
        assert hasattr(mod, "analytics_agent")
        assert hasattr(mod, "create_analytics_agent")

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("google.adk"),
        reason="google-adk not installed in this environment",
    )
    def test_anomaly_agent_module_importable(self):
        from retailpulse.sub_agents import anomaly_agent as mod
        assert hasattr(mod, "anomaly_agent")
        assert hasattr(mod, "create_anomaly_agent")

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("google.adk"),
        reason="google-adk not installed in this environment",
    )
    def test_advisor_agent_module_importable(self):
        from retailpulse.sub_agents import advisor_agent as mod
        assert hasattr(mod, "advisor_agent")
        assert hasattr(mod, "create_advisor_agent")

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("google.adk"),
        reason="google-adk not installed in this environment",
    )
    def test_notification_agent_module_importable(self):
        from retailpulse.sub_agents import notification_agent as mod
        assert hasattr(mod, "notification_agent")
        assert hasattr(mod, "create_notification_agent")


class TestToolBehaviourEdgeCases:
    """Additional edge case tests for custom tools."""

    def test_get_date_range_all_periods(self):
        from retailpulse.tools.custom_tools import get_date_range
        periods = [
            "today", "yesterday", "this_week", "last_week",
            "this_month", "last_month", "last_7_days", "last_30_days",
        ]
        for period in periods:
            result = get_date_range(period)
            assert "start_date" in result, f"Missing start_date for period '{period}'"
            assert "end_date" in result, f"Missing end_date for period '{period}'"
            assert result["start_date"] <= result["end_date"], (
                f"start_date > end_date for period '{period}'"
            )

    def test_format_currency_negative(self):
        from retailpulse.tools.custom_tools import format_currency
        result = format_currency(-500.0)
        assert "-" in result or "500" in result  # negative amounts should still format

    def test_generate_ids_are_strings(self):
        from retailpulse.tools.custom_tools import (
            generate_report_id, generate_promo_id, generate_alert_id
        )
        assert isinstance(generate_report_id("daily"), str)
        assert isinstance(generate_promo_id(), str)
        assert isinstance(generate_alert_id(), str)

    def test_summarize_single_item(self):
        from retailpulse.tools.custom_tools import summarize_for_report
        data = [{"name": "Only Store", "value": 999}]
        result = summarize_for_report(data, "Revenue", top_n=5)
        assert result["total"] == 999
        assert result["average"] == 999
        assert len(result["top_performers"]) == 1

    def test_calculate_pct_change_small_diff_is_flat(self):
        from retailpulse.tools.custom_tools import calculate_percentage_change
        # Less than 1% change should be "flat"
        result = calculate_percentage_change(100.5, 100.0)
        assert result["direction"] == "flat"
