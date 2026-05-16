"""
Promotion & Staffing Advisor Sub-Agent.
Creates data-backed promotion plans and staffing recommendations.
"""

import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from retailpulse.prompts.system_prompts import ADVISOR_PROMPT
from retailpulse.tools.custom_tools import (
    get_date_range,
    format_currency,
    calculate_percentage_change,
    generate_promo_id,
    get_current_timestamp,
    get_day_of_week,
)

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/retailpulse")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")

_mcp_env: dict = {"MDB_MCP_CONNECTION_STRING": MONGODB_URI}


def create_advisor_agent() -> Agent:
    """Creates the promotion and staffing advisor sub-agent."""
    return Agent(
        model=AGENT_MODEL,
        name="advisor_agent",
        description=(
            "Promotion and staffing advisor. Creates data-backed promotion "
            "plans for underperforming tenants and recommends optimal staffing "
            "levels based on footfall forecasts."
        ),
        instruction=ADVISOR_PROMPT,
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
            generate_promo_id,
            get_current_timestamp,
            get_day_of_week,
        ],
    )


advisor_agent = create_advisor_agent()
