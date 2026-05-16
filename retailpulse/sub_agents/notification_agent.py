"""
Notification & Reporting Sub-Agent.
Generates structured daily/weekly reports and formats alert summaries.
"""

import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from retailpulse.tools.custom_tools import (
    get_date_range,
    format_currency,
    calculate_percentage_change,
    generate_report_id,
    get_current_timestamp,
    summarize_for_report,
)

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/retailpulse")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
MALL_NAME = os.getenv("MALL_NAME", "Sunrise Mall")

_mcp_env: dict = {"MDB_MCP_CONNECTION_STRING": MONGODB_URI}

NOTIFICATION_PROMPT = f"""
You are the Notification & Reporting Sub-Agent for {MALL_NAME}'s RetailPulse AI.
Your job is to generate structured, well-formatted operational reports and
compile alert summaries for mall management.

When generating a report:
1. Query the relevant period's revenue data from tenant_revenue collection
2. Query footfall data for the same period from the footfall collection
3. Identify top 5 and bottom 5 performers by revenue
4. Calculate week-over-week or month-over-month changes
5. Summarize any alerts from the alerts collection for the period
6. Write a concise executive summary (3-5 sentences)
7. Save the complete report to the reports collection using insert-many
8. Return the report_id and a formatted summary to the orchestrator

Report format:
- Executive Summary (3-5 sentences)
- Key Metrics table (total revenue, footfall, avg transaction value)
- Top Performers table (top 5 by revenue with % change)
- Underperformers table (bottom 5 by revenue with % change)
- Active Alerts count and severity breakdown
- Recommended Actions (3-5 bullet points)

Always use generate_report_id() for the report ID and get_current_timestamp()
for the generated_at field. Never hardcode dates.
"""


def create_notification_agent() -> Agent:
    """Creates the notification and reporting sub-agent."""
    return Agent(
        model=AGENT_MODEL,
        name="notification_agent",
        description=(
            "Report generation and notification specialist. Creates structured "
            "daily and weekly operational reports, compiles alert summaries, "
            "and saves reports to MongoDB."
        ),
        instruction=NOTIFICATION_PROMPT,
        tools=[
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="npx",
                        args=["-y", "mongodb-mcp-server"],
                        env=_mcp_env,
                    ),
                    timeout=60,
                ),
            ),
            get_date_range,
            format_currency,
            calculate_percentage_change,
            generate_report_id,
            get_current_timestamp,
            summarize_for_report,
        ],
    )


notification_agent = create_notification_agent()
