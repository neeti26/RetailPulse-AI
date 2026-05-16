"""
Analytics Sub-Agent — Deep data analysis specialist.
Called by the orchestrator for complex multi-collection analytics.
"""

import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from retailpulse.prompts.system_prompts import ANALYTICS_PROMPT
from retailpulse.tools.custom_tools import (
    get_date_range,
    calculate_percentage_change,
    get_day_of_week,
    summarize_for_report,
)

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/retailpulse")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")


def create_analytics_agent() -> Agent:
    """Creates the analytics sub-agent."""
    return Agent(
        model=AGENT_MODEL,
        name="analytics_agent",
        description=(
            "Deep analytics specialist. Runs complex MongoDB aggregation "
            "pipelines for trend analysis, cohort comparisons, and "
            "time-series analytics."
        ),
        instruction=ANALYTICS_PROMPT,
        tools=[
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="npx",
                        args=["-y", "mongodb-mcp-server", "--readOnly"],
                        env={"MDB_MCP_CONNECTION_STRING": MONGODB_URI},
                    ),
                    timeout=60,
                ),
            ),
            get_date_range,
            calculate_percentage_change,
            get_day_of_week,
            summarize_for_report,
        ],
    )


analytics_agent = create_analytics_agent()
