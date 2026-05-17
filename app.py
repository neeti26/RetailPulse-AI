"""
RetailPulse AI — Gradio Web UI
Run with: python app.py
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

MALL_NAME = os.getenv("MALL_NAME", "Sunrise Mall")
PORT = int(os.environ.get("PORT", os.getenv("UI_PORT", "8080")))

# ─────────────────────────────────────────────────────────────────────────────
# Agent — lazy-loaded on first message
# ─────────────────────────────────────────────────────────────────────────────
_runner = None
_session_service = None
_session_id = None
_agent_loop = None


def _get_runner():
    global _runner, _session_service, _session_id, _agent_loop
    if _runner is not None:
        return _runner, _session_service, _session_id
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from retailpulse.agent import root_agent
        _agent_loop = asyncio.new_event_loop()
        _session_service = InMemorySessionService()
        _runner = Runner(agent=root_agent, app_name="retailpulse_ui",
                         session_service=_session_service)
        async def _create():
            s = await _session_service.create_session(
                app_name="retailpulse_ui", user_id="mall_manager")
            return s.id
        _session_id = _agent_loop.run_until_complete(_create())
        return _runner, _session_service, _session_id
    except Exception as e:
        raise RuntimeError(f"Agent init failed: {e}")


def chat(message, history):
    """Send a message to the agent and return the response."""
    from google.genai import types as genai_types
    try:
        runner, _, session_id = _get_runner()
        content = genai_types.Content(
            role="user", parts=[genai_types.Part(text=message)])
        full_response = ""
        async def _run():
            nonlocal full_response
            async for event in runner.run_async(
                    user_id="mall_manager", session_id=session_id,
                    new_message=content):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                full_response += part.text
        _agent_loop.run_until_complete(_run())
        return full_response or "No response. Please try again."
    except Exception as e:
        return f"⚠️ Error: {e}\n\nCheck your MongoDB connection and API key."


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────
def load_dashboard():
    import plotly.graph_objects as go
    from retailpulse.dashboard import (
        get_kpi_cards, get_revenue_chart_data, get_footfall_chart_data,
        get_top_tenants_table, get_active_alerts_table, get_category_revenue_data)

    kpis = get_kpi_cards()
    rc = kpis.get("today_revenue_change", 0)
    fc = kpis.get("today_footfall_change", 0)

    kpi_html = f"""
    <div style="display:flex;gap:16px;flex-wrap:wrap;">
      <div style="flex:1;min-width:140px;background:#f0f7ff;border-radius:12px;
                  padding:16px;border-left:4px solid #1a73e8;">
        <div style="font-size:.8em;color:#555;font-weight:600;">TODAY'S REVENUE</div>
        <div style="font-size:1.8em;font-weight:700;">${kpis.get('today_revenue',0):,.0f}</div>
        <div style="font-size:.85em;color:{'green' if rc>=0 else 'red'};">
          {'↑' if rc>0 else '↓'} {abs(rc):.1f}% vs yesterday</div>
      </div>
      <div style="flex:1;min-width:140px;background:#f0fff4;border-radius:12px;
                  padding:16px;border-left:4px solid #34a853;">
        <div style="font-size:.8em;color:#555;font-weight:600;">TODAY'S FOOTFALL</div>
        <div style="font-size:1.8em;font-weight:700;">{kpis.get('today_footfall',0):,}</div>
        <div style="font-size:.85em;color:{'green' if fc>=0 else 'red'};">
          {'↑' if fc>0 else '↓'} {abs(fc):.1f}% vs yesterday</div>
      </div>
      <div style="flex:1;min-width:140px;background:#fff8f0;border-radius:12px;
                  padding:16px;border-left:4px solid #fa7b17;">
        <div style="font-size:.8em;color:#555;font-weight:600;">OPEN ALERTS</div>
        <div style="font-size:1.8em;font-weight:700;
          color:{'#d93025' if kpis.get('active_alerts',0)>0 else '#1a1a1a'};">
          {kpis.get('active_alerts',0)}</div>
      </div>
      <div style="flex:1;min-width:140px;background:#f8f0ff;border-radius:12px;
                  padding:16px;border-left:4px solid #9334e6;">
        <div style="font-size:.8em;color:#555;font-weight:600;">ACTIVE PROMOS</div>
        <div style="font-size:1.8em;font-weight:700;">{kpis.get('active_promotions',0)}</div>
      </div>
    </div>"""

    dates, revenues = get_revenue_chart_data()
    rev_fig = go.Figure()
    if dates:
        rev_fig.add_trace(go.Scatter(x=dates, y=revenues, mode="lines+markers",
            line=dict(color="#1a73e8", width=2.5), fill="tozeroy",
            fillcolor="rgba(26,115,232,0.08)"))
    rev_fig.update_layout(title="14-Day Revenue Trend", height=260,
        plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        margin=dict(l=40,r=20,t=40,b=40))

    hours, counts = get_footfall_chart_data()
    ff_fig = go.Figure()
    if hours:
        ff_fig.add_trace(go.Bar(x=hours, y=counts, marker_color="#34a853"))
    ff_fig.update_layout(title="Today's Hourly Footfall", height=260,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40,r=20,t=40,b=40))

    cats, cat_revs = get_category_revenue_data()
    cat_fig = go.Figure()
    if cats:
        cat_fig.add_trace(go.Pie(labels=cats, values=cat_revs, hole=0.4,
            textinfo="label+percent"))
    cat_fig.update_layout(title="Revenue by Category (This Month)",
        height=260, margin=dict(l=20,r=20,t=40,b=20), showlegend=False)

    top = get_top_tenants_table()
    alerts = get_active_alerts_table()
    return (kpi_html, rev_fig, ff_fig, cat_fig,
            top or [{"Info": "No data — run scripts/seed_data.py"}],
            alerts or [{"Info": "No open alerts 🎉"}])


# ─────────────────────────────────────────────────────────────────────────────
# Quick Actions
# ─────────────────────────────────────────────────────────────────────────────
QUICK_ACTIONS = {
    "🔍 Top Performers": "Show me the top 5 tenants by revenue this week with % change vs last week.",
    "🚨 Anomaly Scan": "Run a full anomaly scan: revenue drops >20%, footfall drops >25%, zero-activity tenants, leases expiring within 60 days. Log issues found.",
    "📊 Weekly Report": "Generate a comprehensive weekly summary report. Include total revenue, footfall, top performers, underperformers. Save to database.",
    "💡 Promotion Plan": "Find the 3 most underperforming tenants this month and create a targeted promotion plan for each. Save to promotions collection.",
    "👣 Footfall Heatmap": "Show hourly footfall breakdown by zone for yesterday. Which zones and hours had highest and lowest traffic?",
    "📋 Active Alerts": "Show all unresolved alerts sorted by severity. What actions do you recommend?",
    "🏪 Tenant Overview": "Give a full overview of all tenants: categories, zones, current month revenue, lease status.",
    "📈 Revenue Trends": "Show revenue trends for the last 30 days. Which categories are growing and which are declining?",
}

WELCOME = f"""Welcome to **RetailPulse AI** — your intelligent operations assistant for **{MALL_NAME}**! 🏬

I can help you:
- 📊 **Analyze** tenant revenue and footfall trends
- 🚨 **Detect** anomalies proactively
- 💡 **Plan** targeted promotions for underperforming tenants
- 📋 **Generate** daily and weekly reports

Use the **Quick Actions** on the left, or ask me anything.

*Try: "Which tenants had the worst performance this week?"*"""

CSS = """
.gradio-container { max-width: 1280px !important; margin: 0 auto !important; }
footer { display: none !important; }
"""

HEADER = f"""
<div style="text-align:center;padding:16px 0 8px 0;border-bottom:1px solid #e8eaed;margin-bottom:12px;">
  <h1 style="font-size:2em;margin:0;color:#1a73e8;font-weight:700;">🏬 RetailPulse AI</h1>
  <p style="color:#555;margin:6px 0 0 0;">Smart Mall Intelligence · <strong>{MALL_NAME}</strong></p>
  <p style="font-size:.82em;color:#999;margin:4px 0 0 0;">
    Google ADK · Gemini 2.5 Flash · MongoDB Atlas MCP · Google Cloud Run</p>
</div>"""


def create_ui():
    import gradio as gr

    with gr.Blocks(css=CSS, title=f"RetailPulse AI — {MALL_NAME}",
                   theme=gr.themes.Soft(primary_hue="blue")) as demo:
        gr.HTML(HEADER)

        with gr.Tabs():
            # ── Dashboard Tab ──────────────────────────────────────────────
            with gr.Tab("📊 Live Dashboard"):
                kpi_display = gr.HTML("<p style='color:#888'>Click Refresh to load live data.</p>")
                with gr.Row():
                    rev_chart = gr.Plot(label="Revenue Trend")
                    ff_chart  = gr.Plot(label="Footfall")
                with gr.Row():
                    cat_chart = gr.Plot(label="Revenue by Category")
                    with gr.Column():
                        gr.Markdown("#### 🚨 Open Alerts")
                        alerts_table = gr.Dataframe(
                            headers=["Severity","Type","Tenant/Zone","Message","Time"],
                            interactive=False, wrap=True)
                gr.Markdown("#### 🏆 Top Tenants This Week")
                top_table = gr.Dataframe(
                    headers=["Tenant","Category","Zone","Revenue (Week)","Transactions"],
                    interactive=False)
                gr.Button("🔄 Refresh Dashboard", variant="primary").click(
                    fn=load_dashboard,
                    outputs=[kpi_display, rev_chart, ff_chart, cat_chart,
                             top_table, alerts_table])
                demo.load(fn=load_dashboard,
                          outputs=[kpi_display, rev_chart, ff_chart, cat_chart,
                                   top_table, alerts_table])

            # ── Chat Tab ───────────────────────────────────────────────────
            with gr.Tab("🤖 AI Assistant"):
                with gr.Row():
                    with gr.Column(scale=1, min_width=210):
                        gr.Markdown("### ⚡ Quick Actions")
                        btns = []
                        for label in QUICK_ACTIONS:
                            btns.append((label, gr.Button(label, variant="secondary", size="sm")))
                        gr.Markdown("---\n**Track:** MongoDB Partner  \n**Model:** Gemini 2.5 Flash  \n**Host:** Cloud Run")

                    with gr.Column(scale=3):
                        chatbot = gr.ChatInterface(
                            fn=chat,
                            chatbot=gr.Chatbot(height=520, render_markdown=True),
                            textbox=gr.Textbox(placeholder="Ask anything about mall operations...",
                                               container=False),
                            examples=[
                                "Which tenants had the highest revenue this week?",
                                "Run the daily anomaly scan",
                                "Find underperforming tenants and create a promotion plan",
                            ],
                        )

                for label, btn in btns:
                    query = QUICK_ACTIONS[label]
                    btn.click(lambda q=query: q, outputs=chatbot.textbox)

    return demo


if __name__ == "__main__":
    print(f"\n🏬 RetailPulse AI — {MALL_NAME}")
    print(f"   Port: {PORT}\n")
    demo = create_ui()
    demo.launch(server_name="0.0.0.0", server_port=PORT)
