"""
RetailPulse AI — Main Agent
Orchestrates MongoDB MCP tools + custom tools + sub-agents via Google ADK.
"""

import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from retailpulse.prompts.system_prompts import ORCHESTRATOR_PROMPT
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
from retailpulse.tools.agentic_tools import (
    validate_tenant_exists,
    plan_campaign_mission,
    record_tool_call,
    validate_query_result,
    compute_revenue_anomaly_score,
    compute_promotion_parameters,
    complete_mission,
)

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/retailpulse")
# gemini-2.5-flash is part of the Gemini 3 model family
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")

# Atlas API credentials (optional — enables Atlas management tools)
ATLAS_CLIENT_ID = os.getenv("MDB_ATLAS_CLIENT_ID", "")
ATLAS_CLIENT_SECRET = os.getenv("MDB_ATLAS_CLIENT_SECRET", "")

# Build MCP server environment
_mcp_env: dict = {
    "MDB_MCP_CONNECTION_STRING": MONGODB_URI,
}
if ATLAS_CLIENT_ID and ATLAS_CLIENT_SECRET:
    _mcp_env["MDB_MCP_API_CLIENT_ID"] = ATLAS_CLIENT_ID
    _mcp_env["MDB_MCP_API_CLIENT_SECRET"] = ATLAS_CLIENT_SECRET


# ─────────────────────────────────────────────────────────────────────────────
# MongoDB MCP Toolset
# ─────────────────────────────────────────────────────────────────────────────
def _build_mongodb_toolset() -> McpToolset:
    """
    Creates the MongoDB MCP toolset connected to the configured cluster.
    Uses npx to run the official mongodb-mcp-server package.
    Full read+write access so the agent can insert promotions, alerts, reports.
    """
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "mongodb-mcp-server"],
                env=_mcp_env,
            ),
            timeout=60,  # Allow up to 60s for complex aggregations
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator Agent
# ─────────────────────────────────────────────────────────────────────────────
def create_agent() -> Agent:
    """
    Creates and returns the main RetailPulse AI orchestrator agent.

    Architecture:
    - Orchestrator handles all user interactions and simple queries directly
    - Delegates to sub-agents for specialised tasks:
        • analytics_agent  — complex aggregations and trend analysis
        • anomaly_agent    — proactive anomaly scanning and alert logging
        • advisor_agent    — promotion planning and staffing recommendations
    - All agents share the MongoDB MCP Server for database access
    - Custom Python tools provide date utilities, formatters, and ID generators
    """
    # Import sub-agents here to avoid circular imports at module load time
    from retailpulse.sub_agents.analytics_agent import analytics_agent
    from retailpulse.sub_agents.anomaly_agent import anomaly_agent
    from retailpulse.sub_agents.advisor_agent import advisor_agent
    from retailpulse.sub_agents.notification_agent import notification_agent

    return Agent(
        model=AGENT_MODEL,
        name="retailpulse_orchestrator",
        description=(
            "RetailPulse AI — Smart Mall Intelligence Agent. "
            "Analyzes footfall, revenue, and operations data to help "
            "mall managers make data-driven decisions. Delegates complex "
            "analytics, anomaly detection, promotion planning, and report "
            "generation to specialised sub-agents."
        ),
        instruction=ORCHESTRATOR_PROMPT,
        # Sub-agents: orchestrator can delegate tasks to these specialists
        sub_agents=[analytics_agent, anomaly_agent, advisor_agent, notification_agent],
        tools=[
            # MongoDB MCP Server — full database superpowers (20+ tools)
            _build_mongodb_toolset(),
            # Utility tools
            get_date_range,
            format_currency,
            calculate_percentage_change,
            generate_report_id,
            generate_promo_id,
            generate_alert_id,
            get_current_timestamp,
            get_day_of_week,
            summarize_for_report,
            # Agentic loop tools — force Reason→Act→Observe→Repeat
            validate_tenant_exists,
            plan_campaign_mission,
            record_tool_call,
            validate_query_result,
            compute_revenue_anomaly_score,
            compute_promotion_parameters,
            complete_mission,
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Module-level agent instance (used by ADK runner and web UI)
# ─────────────────────────────────────────────────────────────────────────────
root_agent = create_agent()
