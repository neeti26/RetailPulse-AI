# 🏬 RetailPulse AI — Autonomous Mall Intelligence Agent

> **Google Cloud Rapid Agent Hackathon 2026**  
> Track: **MongoDB Partner Track**  
> Live Demo: **https://retailpulse-ai-725868889273.us-central1.run.app**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google-ADK%201.33-4285F4?logo=google)](https://google.github.io/adk-docs/)
[![MongoDB MCP](https://img.shields.io/badge/MongoDB-MCP%20Server-00ED64?logo=mongodb)](https://www.mongodb.com/docs/mcp-server/)
[![Cloud Run](https://img.shields.io/badge/Google_Cloud-Cloud_Run-4285F4?logo=googlecloud)](https://cloud.google.com/run)

---

## What Is RetailPulse AI?

RetailPulse AI is a **production-grade autonomous agent** for brick-and-mortar mall operators. It goes far beyond a chatbot — it executes genuine multi-step agentic missions using a strict **Reason → Act → Observe → Repeat** loop.

### The Problem

Mall managers drown in siloed data: footfall sensors, POS transactions, tenant leases, maintenance tickets — all disconnected. They react to problems *after* they happen. A store underperforms for a week before anyone notices. Promotions run on gut feel.

### The Solution

RetailPulse AI is a **proactive, autonomous agent** that:

- 🔍 **Detects anomalies** before managers notice — revenue drops, footfall crashes, lease expiries
- 💡 **Plans promotions** with computed parameters (discount %, timing, expected lift) based on real data
- 📊 **Generates reports** with executive summaries saved to MongoDB
- 🤖 **Executes multi-step missions** — not just answering questions, but completing tasks end-to-end
- 📡 **Observes every action** — structured logging of every MCP tool call, latency, and outcome

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RetailPulse AI                              │
│                                                                     │
│  ┌──────────────┐    ┌─────────────────────────────────────────┐   │
│  │  Gradio UI   │    │     Google ADK Orchestrator Agent        │   │
│  │  (frontend/) │◄──►│     Gemini 2.5 Flash (Gemini 3)         │   │
│  └──────────────┘    │                                         │   │
│                      │  Agentic Loop: Reason→Act→Observe→Repeat│   │
│                      │                                         │   │
│                      │  ┌──────────┐  ┌──────────────────────┐│   │
│                      │  │analytics │  │anomaly_agent         ││   │
│                      │  │_agent    │  │(scans + alerts)      ││   │
│                      │  └──────────┘  └──────────────────────┘│   │
│                      │  ┌──────────┐  ┌──────────────────────┐│   │
│                      │  │advisor   │  │notification_agent    ││   │
│                      │  │_agent    │  │(reports + summaries) ││   │
│                      │  └──────────┘  └──────────────────────┘│   │
│                      └──────────────────┬──────────────────────┘   │
│                                         │                          │
│                      ┌──────────────────▼──────────────────────┐   │
│                      │         MongoDB MCP Server               │   │
│                      │  (mcp_servers/ — 20+ database tools)    │   │
│                      │  find · aggregate · insert-many · atlas  │   │
│                      └──────────────────┬──────────────────────┘   │
│                                         │                          │
│                      ┌──────────────────▼──────────────────────┐   │
│                      │         MongoDB Atlas Cluster            │   │
│                      │  footfall · tenant_revenue · tenants     │   │
│                      │  promotions · alerts · reports           │   │
│                      │  agent_traces (observability)            │   │
│                      └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agentic Loop — How It Actually Works

This is **not** a wrapper that passes prompts to Gemini. The agent executes a strict multi-step loop with observable tool calls:

```
User: "Find underperforming tenants and create promotions"

Step 1 — REASON:   plan_campaign_mission(mission_type='promotion')
                   → Returns 11-step execution plan

Step 2 — ACT:      aggregate(tenant_revenue, [{$match: ...}, {$group: ...}])
                   → Returns 30-day revenue per tenant

Step 3 — OBSERVE:  record_tool_call(tool='aggregate', collection='tenant_revenue', ...)
                   validate_query_result(data, expected_fields=['tenant_id', 'revenue'])
                   → Validates data before proceeding

Step 4 — ACT:      aggregate(footfall, [{$match: ...}, {$group: ...}])
                   → Returns peak hours per zone

Step 5 — OBSERVE:  record_tool_call(...) + validate_query_result(...)

Step 6 — REASON:   compute_promotion_parameters(tenant_id, revenue_decline_pct, peak_hour)
                   → Computes discount %, duration, expected lift from real data

Step 7 — ACT:      insert-many(promotions, [computed_promo_doc])
                   → Writes promotion to MongoDB

Step 8 — VERIFY:   find(promotions, {promo_id: ...})
                   record_tool_call(tool='find', collection='promotions', ...)
                   → Confirms write succeeded

Step 9 — COMPLETE: complete_mission(steps_completed=8, documents_written=1)
                   → Closes the loop with audit trail
```

Every tool call is logged to the `agent_traces` collection in MongoDB for full observability.

---

## Repository Structure

```
retailpulse-ai/
│
├── agents/                        # Agent package (clean imports)
│   └── __init__.py                # Re-exports all agents
│
├── mcp_servers/                   # MCP server documentation & config
│   └── README.md                  # MongoDB MCP server wiring guide
│
├── frontend/                      # Frontend documentation
│   └── README.md                  # Gradio UI structure guide
│
├── retailpulse/                   # Core application package
│   ├── agent.py                   # Main orchestrator (root_agent)
│   ├── dashboard.py               # MongoDB → Plotly data layer
│   ├── observability.py           # Structured logging + trace collection
│   ├── sub_agents/
│   │   ├── analytics_agent.py     # Trend analysis, cohort comparisons
│   │   ├── anomaly_agent.py       # Revenue/footfall anomaly detection
│   │   ├── advisor_agent.py       # Promotion planning with computed params
│   │   └── notification_agent.py  # Report generation + summaries
│   ├── tools/
│   │   ├── custom_tools.py        # Date utils, formatters, ID generators
│   │   └── agentic_tools.py       # Agentic loop tools (plan/act/observe/complete)
│   └── prompts/
│       └── system_prompts.py      # System instructions for all agents
│
├── scripts/
│   └── seed_data.py               # Demo data seeder (90 days, 20 tenants)
│
├── tests/
│   ├── test_agent.py              # Agent configuration tests
│   └── test_tools.py              # Custom tools unit tests (44 tests)
│
├── setup/                         # Deployment scripts
│   ├── RUN_THIS_IN_POWERSHELL.ps1 # One-click Cloud Run deploy
│   ├── 3_mongodb_atlas_setup.md   # Atlas setup guide
│   └── MASTER_DEPLOY_GUIDE.md     # Full deployment checklist
│
├── app.py                         # Gradio web UI (Cloud Run entry point)
├── Dockerfile                     # Container image (Python 3.12 + Node 20)
├── docker-compose.yml             # Local dev stack
├── cloudbuild.yaml                # Cloud Build CI/CD config
├── requirements.txt               # Pinned Python dependencies
├── DEPLOYMENT.md                  # Cloud Run deployment guide
├── DEMO_SCRIPT.md                 # 3-minute demo video script
└── README.md                      # This file
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ (for MongoDB MCP Server via `npx`)
- MongoDB Atlas account (free M0 tier works)
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 1. Clone & Install

```bash
git clone https://github.com/neeti26/RetailPulse-AI
cd RetailPulse-AI
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env:
# MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/retailpulse
# GOOGLE_API_KEY=your_gemini_api_key
```

### 3. Seed Demo Data

```bash
python scripts/seed_data.py
# Seeds: 20 tenants, 90 days revenue, footfall, promotions, alerts
```

### 4. Run

```bash
# Web UI
python app.py
# → http://localhost:8080

# CLI
python -m retailpulse
```

---

## How the MCP Server Is Wired

The MongoDB MCP Server is the agent's "superpower" — it gives every agent direct access to MongoDB Atlas through the Model Context Protocol.

**Each agent spawns the MCP server as a subprocess:**

```python
# From retailpulse/agent.py
McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "MDB_MCP_CONNECTION_STRING": MONGODB_URI,
                # Optional Atlas API:
                # "MDB_MCP_API_CLIENT_ID": ATLAS_CLIENT_ID,
                # "MDB_MCP_API_CLIENT_SECRET": ATLAS_CLIENT_SECRET,
            },
        ),
        timeout=60,
    ),
)
```

**Tools available via MCP:**

| Tool | What the agent uses it for |
|------|---------------------------|
| `aggregate` | Revenue trends, footfall patterns, anomaly detection |
| `find` | Tenant lookup, alert queries, promotion checks |
| `insert-many` | Save promotions, alerts, reports to MongoDB |
| `update-many` | Mark alerts as resolved |
| `collection-schema` | Inspect data structure |
| `atlas-get-performance-advisor` | MongoDB Atlas query optimization |

**Test the MCP server directly:**
```bash
MDB_MCP_CONNECTION_STRING="mongodb+srv://..." npx -y mongodb-mcp-server
```

---

## Observability

Every agent execution is traced and stored in MongoDB's `agent_traces` collection:

```json
{
  "trace_id": "TRACE-20260521-143022",
  "user_query": "Find underperforming tenants and create promotions",
  "total_latency_ms": 8420,
  "tool_calls": [
    {"tool": "aggregate", "collection": "tenant_revenue", "result_count": 20, "latency_ms": 1240},
    {"tool": "aggregate", "collection": "footfall", "result_count": 8, "latency_ms": 890},
    {"tool": "insert-many", "collection": "promotions", "result_count": 3, "latency_ms": 340}
  ],
  "tool_call_count": 8,
  "sub_agent_calls": [{"agent": "advisor_agent", "task": "Create promotion plans"}],
  "success_rate": 100.0,
  "collections_accessed": ["tenant_revenue", "footfall", "promotions"]
}
```

View traces in the **⚙️ Operations** tab → Observability section, or query directly:
```javascript
db.agent_traces.find().sort({started_at: -1}).limit(10)
```

---

## Deploy to Google Cloud Run

```bash
# One command — builds, pushes, deploys
& .\setup\RUN_THIS_IN_POWERSHELL.ps1

# Or manually:
gcloud run deploy retailpulse-ai \
  --image=us-central1-docker.pkg.dev/PROJECT/retailpulse/retailpulse-ai:latest \
  --region=us-central1 \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --set-secrets="MONGODB_URI=MONGODB_URI:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full guide.

---

## Judging Criteria

| Criterion | How RetailPulse AI Delivers |
|-----------|----------------------------|
| **Technological Implementation** | Google ADK multi-agent orchestration · MongoDB MCP Server (20+ tools) · Gemini 2.5 Flash · Strict Reason→Act→Observe→Repeat loop · Structured observability in MongoDB |
| **Design** | Dark-theme Gradio UI · 4 tabs (Overview/Analytics/Operations/AI) · Live Plotly charts · Footfall heatmap · Gradient KPI cards |
| **Potential Impact** | Brick-and-mortar retail is a $5T+ industry · Every mall operator globally is the target user · Proactive anomaly detection prevents revenue loss |
| **Quality of Idea** | Not a chatbot — a genuine autonomous agent · Multi-step missions with observable tool chains · Data-computed promotion parameters · Full audit trail in MongoDB |

---

## License

Apache License 2.0 — see [LICENSE](LICENSE)

---

## Acknowledgments

- [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- [MongoDB MCP Server](https://www.mongodb.com/docs/mcp-server/)
- [Gemini API](https://ai.google.dev/)
- [Google Cloud Run](https://cloud.google.com/run)
