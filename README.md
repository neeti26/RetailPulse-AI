# 🏬 RetailPulse AI — Smart Mall Intelligence Agent

> **Google Cloud Rapid Agent Hackathon Submission**  
> Track: **MongoDB Partner Track**  
> Built with: Google ADK (Agent Development Kit) · Gemini 3 (gemini-2.5-flash) · MongoDB MCP Server · MongoDB Atlas · Google Cloud Run

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google)](https://google.github.io/adk-docs/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-00ED64?logo=mongodb)](https://www.mongodb.com/atlas)
[![Cloud Run](https://img.shields.io/badge/Google_Cloud-Cloud_Run-4285F4?logo=googlecloud)](https://cloud.google.com/run)

---

## 🎯 What is RetailPulse AI?

RetailPulse AI is an autonomous multi-step intelligence agent for **brick-and-mortar mall operators**. It moves far beyond a chatbot — it **reasons, plans, and executes** tasks to help mall managers run smarter operations.

### The Problem
Mall managers today are drowning in data: footfall sensors, POS transactions, tenant lease data, maintenance tickets, and marketing campaign results — all siloed. They react to problems *after* they happen. A store underperforms for a week before anyone notices. A promotion runs with no data backing it. Staffing decisions are made on gut feel.

### The Solution
RetailPulse AI is a **proactive, multi-step agent** that:
- 🔍 **Monitors** real-time shopper traffic and tenant revenue stored in MongoDB Atlas
- 🚨 **Detects anomalies** — sudden footfall drops, revenue dips, inventory shortfalls
- 💡 **Recommends actions** — targeted promotions, staffing adjustments, restocking alerts
- 📊 **Generates reports** — daily/weekly summaries with actionable insights
- 💬 **Answers natural language queries** — "Which tenant had the worst Saturday last month?"
- 🤖 **Executes multi-step missions** — "Find underperforming tenants, draft a promotion plan, and log it to the database"

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RetailPulse AI                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────────────────────────┐  │
│  │   Web UI     │    │         Google ADK Agent             │  │
│  │  (Gradio)    │◄──►│   Orchestrator (Gemini 2.5 Flash)    │  │
│  └──────────────┘    │                                      │  │
│                      │  ┌────────────┐  ┌────────────────┐  │  │
│                      │  │  Analytics │  │  Notification  │  │  │
│                      │  │  Sub-Agent │  │   Sub-Agent    │  │  │
│                      │  └─────┬──────┘  └───────┬────────┘  │  │
│                      └────────┼──────────────────┼───────────┘  │
│                               │                  │              │
│                      ┌────────▼──────────────────▼───────────┐  │
│                      │       MongoDB MCP Server               │  │
│                      │  (find · aggregate · insert · atlas)   │  │
│                      └────────────────┬──────────────────────┘  │
│                                       │                         │
│                      ┌────────────────▼──────────────────────┐  │
│                      │         MongoDB Atlas Cluster          │  │
│                      │  ┌──────────┐  ┌──────────────────┐   │  │
│                      │  │ footfall │  │ tenant_revenue   │   │  │
│                      │  ├──────────┤  ├──────────────────┤   │  │
│                      │  │ tenants  │  │ promotions       │   │  │
│                      │  ├──────────┤  ├──────────────────┤   │  │
│                      │  │ alerts   │  │ reports          │   │  │
│                      │  └──────────┘  └──────────────────┘   │  │
│                      └───────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **Natural Language Queries** | Ask anything: "Show me top 5 tenants by revenue this week" |
| **Anomaly Detection** | Agent proactively scans for revenue/footfall drops > 20% |
| **Promotion Planner** | Multi-step: detect underperformers → draft promotion → save to DB |
| **Automated Reports** | Daily/weekly summaries written to MongoDB and displayed in UI |
| **Staffing Advisor** | Recommends staffing levels based on predicted footfall patterns |
| **Vector Search** | Semantic search across historical reports and tenant notes |
| **Atlas Performance Advisor** | Agent can query MongoDB's own performance recommendations |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ (for MongoDB MCP Server via `npx`)
- MongoDB Atlas account (free tier works) **or** local MongoDB
- Google Cloud project with Vertex AI / Gemini API enabled

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/retailpulse-ai
cd retailpulse-ai
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

```env
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/retailpulse
# OR for local: MONGODB_URI=mongodb://localhost:27017/retailpulse

# Google AI
GOOGLE_API_KEY=your_gemini_api_key
# OR for Vertex AI:
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_CLOUD_LOCATION=us-central1

# Optional: MongoDB Atlas API (for Atlas management tools)
# MDB_ATLAS_CLIENT_ID=your_atlas_client_id
# MDB_ATLAS_CLIENT_SECRET=your_atlas_client_secret
```

### 3. Seed Demo Data

```bash
python scripts/seed_data.py
```

### 4. Run the Agent

```bash
# Interactive CLI
python -m retailpulse

# Web UI (Gradio)
python app.py
```

---

## 💬 Example Agent Interactions

### Simple Query
```
You: Which tenants had the lowest footfall last weekend?

Agent: Let me check the footfall data for last weekend...
[Calls MongoDB MCP: aggregate on footfall collection]

Here are the 5 tenants with lowest footfall (Sat-Sun, May 10-11):
1. TechZone Electronics — 234 visitors (-31% vs prior weekend)
2. Artisan Coffee Co — 412 visitors (-18% vs prior weekend)
3. Vintage Threads — 189 visitors (-42% vs prior weekend)
...
```

### Multi-Step Mission
```
You: Find underperforming tenants this month and create a promotion plan for them

Agent: I'll handle this in steps:

Step 1: Identifying underperforming tenants...
[Calls MongoDB MCP: aggregate on tenant_revenue]
Found 4 tenants with >15% revenue decline this month.

Step 2: Analyzing their historical patterns...
[Calls MongoDB MCP: find on footfall + aggregate]
Peak hours: 2-5pm weekdays. Category: Fashion & Electronics.

Step 3: Drafting promotion plan...
Recommended: "Midweek Boost" — 20% off 2-5pm Tue-Thu for 3 weeks.
Expected lift: +25% footfall based on similar past campaigns.

Step 4: Saving promotion plan to database...
[Calls MongoDB MCP: insert-many on promotions collection]
✅ Promotion plan saved! ID: promo_2026_05_001
```

### Anomaly Alert
```
You: Run the daily anomaly scan

Agent: Running anomaly detection across all tenants...
[Calls MongoDB MCP: aggregate with $group and $cmp]

🚨 ALERTS FOUND (3):
• Food Court Zone B — footfall down 38% vs 7-day avg (possible maintenance issue?)
• Luxury Watches — revenue $0 today (store may be closed?)
• Parking Level 2 — occupancy sensor showing 0 (sensor fault?)

Logging alerts to database...
[Calls MongoDB MCP: insert-many on alerts collection]
✅ 3 alerts logged. Recommend immediate investigation.
```

---

## 📁 Project Structure

```
retailpulse-ai/
├── retailpulse/
│   ├── __init__.py
│   ├── __main__.py           # CLI entry point (python -m retailpulse)
│   ├── agent.py              # Main ADK orchestrator agent
│   ├── sub_agents/
│   │   ├── analytics_agent.py    # Deep analytics sub-agent
│   │   ├── anomaly_agent.py      # Anomaly detection sub-agent
│   │   ├── advisor_agent.py      # Promotion & staffing advisor
│   │   └── notification_agent.py # Report generation sub-agent
│   ├── tools/
│   │   └── custom_tools.py       # Custom Python tools (date utils, formatters, ID generators)
│   └── prompts/
│       └── system_prompts.py     # System instructions for all agents
├── app.py                    # Gradio web UI
├── scripts/
│   └── seed_data.py          # Demo data seeder (90 days, 20 tenants)
├── tests/
│   └── test_tools.py         # Unit tests (29 tests)
├── Dockerfile                # Container image
├── docker-compose.yml        # Local dev stack (app + MongoDB)
├── DEPLOYMENT.md             # Cloud Run deployment guide
├── .env.example              # Environment variable template
├── requirements.txt          # Pinned Python dependencies
└── README.md
```

---

## 🚀 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions. The short version:

```bash
# Local (Docker Compose — fastest for demo)
cp .env.example .env   # add GOOGLE_API_KEY + MONGODB_URI
docker compose up --build
# Open http://localhost:7860

# Google Cloud Run (for hosted submission URL)
gcloud run deploy retailpulse-ai \
  --image gcr.io/$PROJECT_ID/retailpulse-ai \
  --region us-central1 --allow-unauthenticated --port 7860
```

---

## 🏆 Hackathon Judging Criteria

| Criterion | How RetailPulse AI Delivers |
|---|---|
| **Technological Implementation** | Google ADK multi-agent orchestration + MongoDB MCP Server (20+ tools) + Gemini 2.5 Flash reasoning + Vector Search |
| **Design** | Clean Gradio UI, structured agent responses, clear multi-step reasoning traces |
| **Potential Impact** | Brick-and-mortar retail is a $5T+ industry; mall operators globally can use this |
| **Quality of Idea** | Proactive anomaly detection + multi-step autonomous missions, not just Q&A |

---

## 📄 License

Apache License 2.0 — see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- [MongoDB MCP Server](https://www.mongodb.com/docs/mcp-server/)
- [Gemini API](https://ai.google.dev/)
