# RetailPulse AI — 3-Minute Demo Script

> Use this script when recording your Devpost demo video.
> Target: exactly 3 minutes. Practice twice before recording.

---

## Setup Before Recording

1. `python scripts/seed_data.py` — ensure fresh demo data
2. `python app.py` — start the UI
3. Open `http://localhost:7860` in a clean browser window (no other tabs)
4. Have OBS or Loom ready to record screen + microphone

---

## Script (3:00)

### [0:00 – 0:20] Hook & Problem Statement

> *Show the Dashboard tab loading with live KPI cards and charts*

**Say:**
"Mall managers today are drowning in siloed data — footfall sensors, POS systems,
tenant leases — all disconnected. They react to problems after they happen.
RetailPulse AI changes that. It's a proactive, multi-step intelligence agent
built with Google ADK, Gemini 3, and MongoDB Atlas."

---

### [0:20 – 0:45] Dashboard Tour

> *Point to the KPI cards, revenue trend chart, footfall chart, and alerts table*

**Say:**
"The live dashboard pulls real-time data directly from MongoDB Atlas.
You can see today's revenue, footfall, open alerts, and active promotions
at a glance. All of this is live data — no hardcoded numbers."

> *Click Refresh Dashboard to show it actually fetches from MongoDB*

---

### [0:45 – 1:15] Multi-Step Mission — Anomaly Scan

> *Switch to the AI Assistant tab. Click "🚨 Anomaly Scan"*

**Say:**
"Now watch the agent work. I'll ask it to run a full anomaly scan.
It doesn't just answer — it plans and executes multiple steps."

> *Wait for response. Point out the step-by-step reasoning*

**Say:**
"The agent used the MongoDB MCP Server to run aggregation pipelines across
the footfall and revenue collections, detected the Zone-C footfall drop,
and automatically logged the alert to MongoDB. That's a real write operation
— not a simulation."

---

### [1:15 – 1:50] Multi-Step Mission — Promotion Plan

> *Click "💡 Promotion Plan"*

**Say:**
"Now let's go further. I'll ask it to find underperforming tenants and
create a data-backed promotion plan — a true multi-step mission."

> *Wait for response. Point out: Step 1 query, Step 2 analysis, Step 3 plan, Step 4 save*

**Say:**
"Four steps, fully autonomous. It queried historical revenue, identified
the underperformers, designed targeted promotions based on their peak hours,
and saved the plans directly to MongoDB. The mall manager stays in control
but the agent does the heavy lifting."

---

### [1:50 – 2:20] Natural Language Query

> *Type in the chat: "Compare this month's revenue to last month by category"*

**Say:**
"The agent handles natural language queries too. No SQL, no dashboards to
configure — just ask."

> *Wait for response showing the comparison table with trend indicators*

**Say:**
"It ran a MongoDB aggregation pipeline, calculated the month-over-month
changes, and presented it with trend indicators. This is the analytics
sub-agent at work — one of four specialist agents the orchestrator can
delegate to."

---

### [2:20 – 2:45] Architecture Callout

> *Briefly show the README architecture diagram or draw on screen*

**Say:**
"Under the hood: Google ADK orchestrates four specialist sub-agents.
Each one connects to MongoDB Atlas through the official MongoDB MCP Server —
that's the partner integration. The MCP server gives the agents 20+ tools:
find, aggregate, insert, atlas performance advisor, vector search.
Deployed on Google Cloud Run for the hosted URL."

---

### [2:45 – 3:00] Closing

**Say:**
"RetailPulse AI turns a mall manager's most time-consuming tasks —
anomaly detection, promotion planning, reporting — into one-click
autonomous missions. The code is open source on GitHub under Apache 2.0.
Thank you."

> *End recording*

---

## Tips

- Speak at a measured pace — don't rush
- If the agent takes >15s, narrate what it's doing: "It's running the aggregation pipeline now..."
- Keep the browser zoom at 100% so charts are readable
- Record at 1920×1080 minimum
- Upload to YouTube (unlisted) and paste the link in your Devpost submission
