"""
Anomaly Detection Sub-Agent — Proactive problem scanner.
Detects revenue drops, footfall anomalies, sensor faults, and lease expiries.
"""

import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from retailpulse.prompts.system_prompts import ANOMALY_PROMPT
from retailpulse.tools.custom_tools import (
    get_date_range,
    calculate_percentage_change,
    generate_alert_id,
    get_current_timestamp,
)

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/retailpulse")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
ATLAS_CLIENT_ID = os.getenv("MDB_ATLAS_CLIENT_ID", "")
ATLAS_CLIENT_SECRET = os.getenv("MDB_ATLAS_CLIENT_SECRET", "")

_mcp_env: dict = {"MDB_MCP_CONNECTION_STRING": MONGODB_URI}
if ATLAS_CLIENT_ID and ATLAS_CLIENT_SECRET:
    _mcp_env["MDB_MCP_API_CLIENT_ID"] = ATLAS_CLIENT_ID
    _mcp_env["MDB_MCP_API_CLIENT_SECRET"] = ATLAS_CLIENT_SECRET


def create_anomaly_agent() -> Agent:
    """Creates the anomaly detection sub-agent."""
    return Agent(
        model=AGENT_MODEL,
        name="anomaly_agent",
        description=(
            "Proactive anomaly detection specialist. Scans revenue, footfall, "
            "and operational data to surface problems before they escalate. "
            "Logs all detected anomalies to the alerts collection."
        ),
        instruction=ANOMALY_PROMPT,
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
            calculate_percentage_change,
            generate_alert_id,
            get_current_timestamp,
        ],
    )


anomaly_agent = create_anomaly_agent()
