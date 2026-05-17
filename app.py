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
    alerts_count = kpis.get("active_alerts", 0)

    kpi_html = f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:8px 0 16px 0;">
      <div style="flex:1;min-width:150px;background:linear-gradient(135deg,#1a73e8,#0d47a1);
                  border-radius:16px;padding:20px;color:white;box-shadow:0 4px 15px rgba(26,115,232,0.3);">
        <div style="font-size:.75em;font-weight:700;letter-spacing:1px;opacity:.85;">TODAY'S REVENUE</div>
        <div style="font-size:2em;font-weight:800;margin:6px 0;">${kpis.get('today_revenue',0):,.0f}</div>
        <div style="font-size:.82em;opacity:.9;">{'↑' if rc>=0 else '↓'} {abs(rc):.1f}% vs yesterday</div>
      </div>
      <div style="flex:1;min-width:150px;background:linear-gradient(135deg,#00c853,#1b5e20);
                  border-radius:16px;padding:20px;color:white;box-shadow:0 4px 15px rgba(0,200,83,0.3);">
        <div style="font-size:.75em;font-weight:700;letter-spacing:1px;opacity:.85;">TODAY'S FOOTFALL</div>
        <div style="font-size:2em;font-weight:800;margin:6px 0;">{kpis.get('today_footfall',0):,}</div>
        <div style="font-size:.82em;opacity:.9;">{'↑' if fc>=0 else '↓'} {abs(fc):.1f}% vs yesterday</div>
      </div>
      <div style="flex:1;min-width:150px;background:{'linear-gradient(135deg,#d32f2f,#b71c1c)' if alerts_count>0 else 'linear-gradient(135deg,#546e7a,#263238)'};
                  border-radius:16px;padding:20px;color:white;box-shadow:0 4px 15px rgba(0,0,0,0.2);">
        <div style="font-size:.75em;font-weight:700;letter-spacing:1px;opacity:.85;">OPEN ALERTS</div>
        <div style="font-size:2em;font-weight:800;margin:6px 0;">{alerts_count}</div>
        <div style="font-size:.82em;opacity:.9;">{'🚨 Needs attention' if alerts_count>0 else '✅ All clear'}</div>
      </div>
      <div style="flex:1;min-width:150px;background:linear-gradient(135deg,#7b1fa2,#4a148c);
                  border-radius:16px;padding:20px;color:white;box-shadow:0 4px 15px rgba(123,31,162,0.3);">
        <div style="font-size:.75em;font-weight:700;letter-spacing:1px;opacity:.85;">ACTIVE PROMOS</div>
        <div style="font-size:2em;font-weight:800;margin:6px 0;">{kpis.get('active_promotions',0)}</div>
        <div style="font-size:.82em;opacity:.9;">{kpis.get('total_tenants',0)} total tenants</div>
      </div>
    </div>"""

    # Revenue chart
    dates, revenues = get_revenue_chart_data()
    rev_fig = go.Figure()
    if dates:
        rev_fig.add_trace(go.Scatter(
            x=dates, y=revenues, mode="lines+markers",
            line=dict(color="#1a73e8", width=3),
            marker=dict(size=7, color="#1a73e8"),
            fill="tozeroy", fillcolor="rgba(26,115,232,0.1)",
            name="Revenue"))
    rev_fig.update_layout(
        title=dict(text="📈 14-Day Revenue Trend", font=dict(size=15, color="#1a1a1a")),
        height=280, plot_bgcolor="#fafafa", paper_bgcolor="white",
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f0f0f0"),
        xaxis=dict(gridcolor="#f0f0f0"),
        margin=dict(l=50, r=20, t=45, b=40),
        hovermode="x unified")

    # Footfall chart
    hours, counts = get_footfall_chart_data()
    ff_fig = go.Figure()
    if hours:
        colors = ["#1a73e8" if c == max(counts) else
                  "#ea4335" if c == min(counts) else "#4285f4"
                  for c in counts]
        ff_fig.add_trace(go.Bar(x=hours, y=counts, marker_color=colors,
                                name="Visitors"))
    ff_fig.update_layout(
        title=dict(text="👣 Today's Hourly Footfall", font=dict(size=15, color="#1a1a1a")),
        height=280, plot_bgcolor="#fafafa", paper_bgcolor="white",
        yaxis=dict(gridcolor="#f0f0f0"),
        xaxis=dict(gridcolor="#f0f0f0"),
        margin=dict(l=40, r=20, t=45, b=40))

    # Category pie
    cats, cat_revs = get_category_revenue_data()
    cat_fig = go.Figure()
    if cats:
        cat_fig.add_trace(go.Pie(
            labels=cats, values=cat_revs, hole=0.45,
            textinfo="label+percent",
            marker=dict(colors=["#1a73e8","#34a853","#fa7b17","#9334e6",
                                 "#ea4335","#00bcd4","#ff9800","#607d8b"]),
            textfont=dict(size=12)))
    cat_fig.update_layout(
        title=dict(text="🏷️ Revenue by Category (This Month)",
                   font=dict(size=15, color="#1a1a1a")),
        height=280, margin=dict(l=20, r=20, t=45, b=20), showlegend=False,
        paper_bgcolor="white")

    top = get_top_tenants_table()
    alerts = get_active_alerts_table()
    return (kpi_html, rev_fig, ff_fig, cat_fig,
            top or [{"Info": "No data — run scripts/seed_data.py"}],
            alerts or [{"Info": "✅ No open alerts"}])


# ─────────────────────────────────────────────────────────────────────────────
# Quick Actions & UI
# ─────────────────────────────────────────────────────────────────────────────
QUICK_ACTIONS = {
    "🔍 Top Performers": "Show me the top 5 tenants by revenue this week with % change vs last week.",
    "🚨 Anomaly Scan": "Run a full anomaly scan: revenue drops >20%, footfall drops >25%, zero-activity tenants, leases expiring within 60 days. Log all issues found.",
    "📊 Weekly Report": "Generate a comprehensive weekly summary report. Include total revenue, footfall, top performers, underperformers, and key insights. Save to database.",
    "💡 Promotion Plan": "Find the 3 most underperforming tenants this month and create a targeted promotion plan for each. Save to promotions collection.",
    "👣 Footfall Heatmap": "Show hourly footfall breakdown by zone for yesterday. Which zones and hours had highest and lowest traffic?",
    "📋 Active Alerts": "Show all unresolved alerts sorted by severity. What actions do you recommend for each?",
    "🏪 Tenant Overview": "Give a full overview of all tenants: categories, zones, current month revenue, and lease status.",
    "📈 Revenue Trends": "Show revenue trends for the last 30 days. Which categories are growing and which are declining?",
}

CSS = """
.gradio-container { max-width: 1300px !important; margin: 0 auto !important; }
footer { display: none !important; }
.tab-nav { border-bottom: 2px solid #e8eaed !important; }
.tab-nav button { font-size: 15px !important; font-weight: 600 !important; padding: 12px 20px !important; }
.tab-nav button.selected { color: #1a73e8 !important; border-bottom: 3px solid #1a73e8 !important; }
.quick-btn { text-align: left !important; justify-content: flex-start !important; }
"""

HEADER = f"""
<div style="background:linear-gradient(135deg,#1a73e8 0%,#0d47a1 50%,#1565c0 100%);
            padding:28px 32px;border-radius:0 0 24px 24px;margin-bottom:20px;
            box-shadow:0 4px 20px rgba(26,115,232,0.4);">
  <div style="display:flex;align-items:center;gap:16px;">
    <div style="font-size:3em;">🏬</div>
    <div>
      <h1 style="font-size:2.2em;margin:0;color:white;font-weight:800;letter-spacing:-0.5px;">
        RetailPulse AI</h1>
      <p style="color:rgba(255,255,255,0.85);margin:4px 0 0 0;font-size:1.05em;">
        Smart Mall Intelligence Agent &nbsp;·&nbsp; <strong>{MALL_NAME}</strong></p>
      <p style="color:rgba(255,255,255,0.65);margin:4px 0 0 0;font-size:0.82em;">
        Google ADK &nbsp;·&nbsp; Gemini 2.5 Flash &nbsp;·&nbsp;
        MongoDB Atlas MCP &nbsp;·&nbsp; Google Cloud Run</p>
    </div>
    <div style="margin-left:auto;text-align:right;">
      <div style="background:rgba(255,255,255,0.15);border-radius:12px;padding:10px 16px;">
        <div style="color:rgba(255,255,255,0.7);font-size:.75em;font-weight:600;">HACKATHON</div>
        <div style="color:white;font-weight:700;font-size:.9em;">MongoDB Partner Track</div>
        <div style="color:rgba(255,255,255,0.7);font-size:.75em;">Google Cloud Rapid Agent 2026</div>
      </div>
    </div>
  </div>
</div>"""


def create_ui():
    import gradio as gr

    with gr.Blocks(css=CSS, title=f"RetailPulse AI — {MALL_NAME}",
                   theme=gr.themes.Soft(primary_hue="blue",
                                        neutral_hue="slate")) as demo:
        gr.HTML(HEADER)

        with gr.Tabs(elem_classes=["tab-nav"]):

            # ── Dashboard Tab ──────────────────────────────────────────────
            with gr.Tab("📊 Live Dashboard"):
                kpi_display = gr.HTML(
                    "<div style='text-align:center;padding:20px;color:#888;'>"
                    "Click <b>🔄 Refresh Dashboard</b> to load live data from MongoDB Atlas</div>")

                with gr.Row():
                    rev_chart = gr.Plot(label="Revenue Trend")
                    ff_chart  = gr.Plot(label="Footfall")

                with gr.Row():
                    cat_chart = gr.Plot(label="Revenue by Category")
                    with gr.Column():
                        gr.Markdown("### 🚨 Open Alerts")
                        alerts_table = gr.Dataframe(
                            headers=["Severity","Type","Tenant/Zone","Message","Time"],
                            interactive=False, wrap=True,
                            column_widths=["80px","100px","120px","auto","100px"])

                gr.Markdown("### 🏆 Top Tenants This Week")
                top_table = gr.Dataframe(
                    headers=["Tenant","Category","Zone","Revenue (Week)","Transactions"],
                    interactive=False)

                gr.Button("🔄 Refresh Dashboard", variant="primary", size="lg").click(
                    fn=load_dashboard,
                    outputs=[kpi_display, rev_chart, ff_chart, cat_chart,
                             top_table, alerts_table])

                demo.load(fn=load_dashboard,
                          outputs=[kpi_display, rev_chart, ff_chart, cat_chart,
                                   top_table, alerts_table])

            # ── Chat Tab ───────────────────────────────────────────────────
            with gr.Tab("🤖 AI Assistant"):
                with gr.Row():
                    # Quick actions sidebar
                    with gr.Column(scale=1, min_width=220):
                        gr.Markdown("### ⚡ Quick Actions")
                        gr.Markdown("*One click to run a full analysis*")
                        btns = []
                        for label in QUICK_ACTIONS:
                            b = gr.Button(label, variant="secondary", size="sm",
                                          elem_classes=["quick-btn"])
                            btns.append((label, b))

                        gr.Markdown("---")
                        gr.HTML("""
                        <div style="background:#f8f9fa;border-radius:12px;padding:14px;
                                    border:1px solid #e8eaed;">
                          <div style="font-weight:700;color:#1a1a1a;margin-bottom:8px;">🛠️ Tech Stack</div>
                          <div style="font-size:.82em;color:#555;line-height:1.8;">
                            🤖 Google ADK 1.33<br>
                            ✨ Gemini 2.5 Flash<br>
                            🍃 MongoDB Atlas MCP<br>
                            ☁️ Google Cloud Run<br>
                            🐍 Python 3.12
                          </div>
                        </div>""")

                    # Chat area
                    with gr.Column(scale=3):
                        chatbot = gr.ChatInterface(
                            fn=chat,
                            chatbot=gr.Chatbot(
                                height=500,
                                render_markdown=True,
                                placeholder="<div style='text-align:center;padding:40px;color:#888;'>"
                                           "<div style='font-size:3em;margin-bottom:12px;'>🏬</div>"
                                           "<div style='font-size:1.1em;font-weight:600;'>RetailPulse AI</div>"
                                           "<div style='margin-top:8px;'>Ask me anything about mall operations</div>"
                                           "</div>",
                                avatar_images=(None, "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg"),
                            ),
                            textbox=gr.Textbox(
                                placeholder="Ask anything about mall operations...",
                                container=False, scale=7),
                            examples=[
                                "Which tenants had the highest revenue this week?",
                                "Run the daily anomaly scan and log any issues",
                                "Find underperforming tenants and create a promotion plan",
                                "Compare this month's revenue to last month by category",
                            ],
                            submit_btn="Send ➤",
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
