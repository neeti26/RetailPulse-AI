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
# Dashboard builders
# ─────────────────────────────────────────────────────────────────────────────
def _arrow(v):
    return ("↑", "green") if v > 0 else (("↓", "#d32f2f") if v < 0 else ("→", "#888"))


def build_kpi_html(kpis: dict) -> str:
    rc = kpis.get("today_revenue_change", 0)
    fc = kpis.get("today_footfall_change", 0)
    wc = kpis.get("week_revenue_change", 0)
    al = kpis.get("active_alerts", 0)
    ra, rc_col = _arrow(rc)
    fa, fc_col = _arrow(fc)
    wa, wc_col = _arrow(wc)

    def card(bg, icon, label, value, sub, sub_col="#fff"):
        return f"""
        <div style="flex:1;min-width:160px;background:{bg};border-radius:16px;
                    padding:20px 22px;color:white;box-shadow:0 6px 20px rgba(0,0,0,0.18);
                    transition:transform .2s;" onmouseover="this.style.transform='translateY(-3px)'"
                    onmouseout="this.style.transform='translateY(0)'">
          <div style="font-size:1.6em;margin-bottom:6px;">{icon}</div>
          <div style="font-size:.72em;font-weight:700;letter-spacing:1.2px;opacity:.8;">{label}</div>
          <div style="font-size:1.9em;font-weight:800;margin:4px 0;">{value}</div>
          <div style="font-size:.82em;color:{sub_col};">{sub}</div>
        </div>"""

    return f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:8px 0 20px 0;">
      {card("linear-gradient(135deg,#1565c0,#1a73e8)", "💰", "TODAY'S REVENUE",
            f"${kpis.get('today_revenue',0):,.0f}",
            f"{ra} {abs(rc):.1f}% vs yesterday", rc_col)}
      {card("linear-gradient(135deg,#1b5e20,#2e7d32)", "👣", "TODAY'S FOOTFALL",
            f"{kpis.get('today_footfall',0):,}",
            f"{fa} {abs(fc):.1f}% vs yesterday", fc_col)}
      {card("linear-gradient(135deg,#4a148c,#7b1fa2)", "📅", "WEEK REVENUE",
            f"${kpis.get('week_revenue',0):,.0f}",
            f"{wa} {abs(wc):.1f}% vs last week", wc_col)}
      {card("linear-gradient(135deg,#e65100,#f57c00)" if al > 0 else "linear-gradient(135deg,#1b5e20,#388e3c)",
            "🚨" if al > 0 else "✅", "OPEN ALERTS",
            str(al),
            "Needs attention" if al > 0 else "All clear")}
      {card("linear-gradient(135deg,#880e4f,#c2185b)", "🎯", "ACTIVE PROMOS",
            str(kpis.get('active_promotions',0)),
            f"{kpis.get('total_tenants',0)} tenants total")}
      {card("linear-gradient(135deg,#006064,#00838f)", "📊", "MONTH REVENUE",
            f"${kpis.get('month_revenue',0):,.0f}",
            "Month to date")}
    </div>"""


def load_overview():
    """Load the main overview dashboard."""
    import plotly.graph_objects as go
    from retailpulse.dashboard import (
        get_kpi_cards, get_revenue_chart_data, get_footfall_chart_data,
        get_top_tenants_table, get_active_alerts_table, get_category_revenue_data,
        get_zone_revenue_data)

    kpis = get_kpi_cards()
    kpi_html = build_kpi_html(kpis)

    # Revenue trend (30 days)
    dates, revenues = get_revenue_chart_data(30)
    rev_fig = go.Figure()
    if dates:
        rev_fig.add_trace(go.Scatter(
            x=dates, y=revenues, mode="lines+markers",
            line=dict(color="#1a73e8", width=3),
            marker=dict(size=6, color="#1a73e8",
                        line=dict(color="white", width=2)),
            fill="tozeroy", fillcolor="rgba(26,115,232,0.08)",
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>"))
    rev_fig.update_layout(
        title=dict(text="📈 30-Day Revenue Trend", font=dict(size=14, color="#1a1a1a")),
        height=260, plot_bgcolor="#fafafa", paper_bgcolor="white",
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f0f0f0",
                   zeroline=False),
        xaxis=dict(gridcolor="#f0f0f0", tickangle=-30),
        margin=dict(l=60, r=20, t=45, b=50), hovermode="x unified",
        showlegend=False)

    # Hourly footfall
    hours, counts = get_footfall_chart_data()
    ff_fig = go.Figure()
    if hours and counts:
        max_v = max(counts)
        min_v = min(counts)
        colors = ["#d32f2f" if c == max_v else
                  "#1565c0" if c == min_v else "#42a5f5"
                  for c in counts]
        ff_fig.add_trace(go.Bar(
            x=hours, y=counts, marker_color=colors,
            hovertemplate="<b>%{x}</b><br>Visitors: %{y:,}<extra></extra>"))
    ff_fig.update_layout(
        title=dict(text="👣 Today's Hourly Footfall", font=dict(size=14, color="#1a1a1a")),
        height=260, plot_bgcolor="#fafafa", paper_bgcolor="white",
        yaxis=dict(gridcolor="#f0f0f0", zeroline=False),
        xaxis=dict(gridcolor="#f0f0f0"),
        margin=dict(l=40, r=20, t=45, b=40), showlegend=False)

    # Category donut
    cats, cat_revs = get_category_revenue_data()
    cat_fig = go.Figure()
    if cats:
        cat_fig.add_trace(go.Pie(
            labels=cats, values=cat_revs, hole=0.5,
            textinfo="label+percent",
            marker=dict(colors=["#1a73e8","#34a853","#fa7b17","#9334e6",
                                 "#ea4335","#00bcd4","#ff9800","#607d8b"],
                        line=dict(color="white", width=2)),
            textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>"))
    cat_fig.update_layout(
        title=dict(text="🏷️ Revenue by Category (This Month)",
                   font=dict(size=14, color="#1a1a1a")),
        height=260, margin=dict(l=10, r=10, t=45, b=10),
        showlegend=False, paper_bgcolor="white")

    # Zone bar
    zones, zone_revs = get_zone_revenue_data()
    zone_fig = go.Figure()
    if zones:
        zone_fig.add_trace(go.Bar(
            x=zones, y=zone_revs,
            marker=dict(color=zone_revs,
                        colorscale="Blues", showscale=False,
                        line=dict(color="white", width=1)),
            hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>"))
    zone_fig.update_layout(
        title=dict(text="🗺️ Revenue by Zone (This Month)",
                   font=dict(size=14, color="#1a1a1a")),
        height=260, plot_bgcolor="#fafafa", paper_bgcolor="white",
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f0f0f0",
                   zeroline=False),
        margin=dict(l=60, r=20, t=45, b=40), showlegend=False)

    top = get_top_tenants_table(10)
    alerts = get_active_alerts_table()
    return (kpi_html, rev_fig, ff_fig, cat_fig, zone_fig,
            top or [{"Info": "No data — run scripts/seed_data.py"}],
            alerts or [{"Info": "✅ No open alerts"}])


def load_analytics():
    """Load the analytics tab."""
    import plotly.graph_objects as go
    from retailpulse.dashboard import (
        get_revenue_by_category_trend, get_footfall_heatmap_data,
        get_weekly_footfall_trend, get_underperformers_table)

    # Category trend lines
    cat_trends = get_revenue_by_category_trend(30)
    trend_fig = go.Figure()
    colors = ["#1a73e8","#34a853","#fa7b17","#9334e6",
              "#ea4335","#00bcd4","#ff9800","#607d8b"]
    for i, (cat, (dates, revs)) in enumerate(cat_trends.items()):
        trend_fig.add_trace(go.Scatter(
            x=dates, y=revs, mode="lines", name=cat,
            line=dict(color=colors[i % len(colors)], width=2.5),
            hovertemplate=f"<b>{cat}</b><br>%{{x}}<br>$%{{y:,.0f}}<extra></extra>"))
    trend_fig.update_layout(
        title=dict(text="📊 Revenue by Category — 30-Day Trend",
                   font=dict(size=14, color="#1a1a1a")),
        height=320, plot_bgcolor="#fafafa", paper_bgcolor="white",
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f0f0f0"),
        xaxis=dict(gridcolor="#f0f0f0", tickangle=-30),
        margin=dict(l=60, r=20, t=45, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified")

    # Footfall heatmap
    zones, hours, matrix = get_footfall_heatmap_data()
    heat_fig = go.Figure()
    if zones and hours and matrix:
        heat_fig.add_trace(go.Heatmap(
            z=matrix, x=hours, y=zones,
            colorscale="YlOrRd",
            hovertemplate="<b>%{y}</b> at %{x}<br>Avg visitors: %{z:,.0f}<extra></extra>",
            colorbar=dict(title="Visitors")))
    heat_fig.update_layout(
        title=dict(text="🔥 Footfall Heatmap — Zone × Hour (7-Day Avg)",
                   font=dict(size=14, color="#1a1a1a")),
        height=320, paper_bgcolor="white",
        xaxis=dict(title="Hour of Day"),
        yaxis=dict(title="Zone"),
        margin=dict(l=80, r=20, t=45, b=60))

    # Weekly footfall trend
    ff_dates, ff_counts = get_weekly_footfall_trend()
    ff_trend_fig = go.Figure()
    if ff_dates:
        ff_trend_fig.add_trace(go.Scatter(
            x=ff_dates, y=ff_counts, mode="lines+markers",
            line=dict(color="#34a853", width=3),
            marker=dict(size=7, color="#34a853",
                        line=dict(color="white", width=2)),
            fill="tozeroy", fillcolor="rgba(52,168,83,0.08)",
            hovertemplate="<b>%{x}</b><br>Visitors: %{y:,}<extra></extra>"))
    ff_trend_fig.update_layout(
        title=dict(text="👣 14-Day Footfall Trend",
                   font=dict(size=14, color="#1a1a1a")),
        height=280, plot_bgcolor="#fafafa", paper_bgcolor="white",
        yaxis=dict(gridcolor="#f0f0f0", zeroline=False),
        xaxis=dict(gridcolor="#f0f0f0", tickangle=-30),
        margin=dict(l=50, r=20, t=45, b=50), showlegend=False,
        hovermode="x unified")

    underperformers = get_underperformers_table()
    return (trend_fig, heat_fig, ff_trend_fig,
            underperformers or [{"Info": "No underperformers — all tenants healthy! 🎉"}])


def load_operations():
    """Load the operations tab (alerts, promotions, leases)."""
    from retailpulse.dashboard import (
        get_active_alerts_table, get_promotions_table, get_lease_expiry_table)
    alerts = get_active_alerts_table()
    promos = get_promotions_table()
    leases = get_lease_expiry_table()
    return (
        alerts or [{"Info": "✅ No open alerts"}],
        promos or [{"Info": "No active promotions"}],
        leases or [{"Info": "No leases expiring soon"}],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Quick Actions
# ─────────────────────────────────────────────────────────────────────────────
QUICK_ACTIONS = {
    "🔍 Top Performers": "Show me the top 5 tenants by revenue this week with % change vs last week. Format as a table.",
    "🚨 Anomaly Scan": "Run a full anomaly scan: check revenue drops >20%, footfall drops >25%, zero-activity tenants, and leases expiring within 60 days. Log all issues found to the alerts collection.",
    "📊 Weekly Report": "Generate a comprehensive weekly summary report. Include total revenue, footfall, top 5 performers, bottom 3 underperformers, and 3 key action items. Save to the reports collection.",
    "💡 Promotion Plan": "Find the 3 most underperforming tenants this month. For each, analyze their peak hours and create a targeted promotion plan. Save all plans to the promotions collection.",
    "👣 Footfall Analysis": "Show hourly footfall breakdown by zone for yesterday. Identify peak hours, dead zones, and give 3 specific recommendations to improve traffic.",
    "📋 Active Alerts": "Show all unresolved alerts sorted by severity. For each CRITICAL or HIGH alert, provide a specific recommended action.",
    "📈 Revenue vs Last Month": "Compare this month's revenue to last month by category. Show % change, identify the biggest winner and biggest loser, and explain likely causes.",
    "🏪 Tenant Health Check": "Run a full tenant health check: revenue trend, lease status, and anomaly history for all 20 tenants. Flag any that need immediate attention.",
}

CSS = """
.gradio-container { max-width: 1400px !important; margin: 0 auto !important; }
footer { display: none !important; }
.tab-nav button { font-size: 14px !important; font-weight: 600 !important; padding: 10px 18px !important; }
.quick-btn { text-align: left !important; justify-content: flex-start !important; font-size: 12px !important; }
.gr-button-primary { background: linear-gradient(135deg, #1a73e8, #0d47a1) !important; border: none !important; }
"""

HEADER = f"""
<div style="background:linear-gradient(135deg,#0d47a1 0%,#1565c0 40%,#1a73e8 100%);
            padding:24px 32px 20px 32px;border-radius:0 0 20px 20px;margin-bottom:16px;
            box-shadow:0 6px 24px rgba(13,71,161,0.45);">
  <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
    <div style="font-size:3.2em;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.3));">🏬</div>
    <div style="flex:1;">
      <h1 style="font-size:2em;margin:0;color:white;font-weight:800;letter-spacing:-0.5px;
                 text-shadow:0 2px 4px rgba(0,0,0,0.2);">RetailPulse AI</h1>
      <p style="color:rgba(255,255,255,0.88);margin:3px 0 0 0;font-size:1em;">
        Autonomous Mall Intelligence Agent &nbsp;·&nbsp; <strong>{MALL_NAME}</strong></p>
      <p style="color:rgba(255,255,255,0.6);margin:3px 0 0 0;font-size:.78em;letter-spacing:.3px;">
        Google ADK &nbsp;·&nbsp; Gemini 2.5 Flash (Gemini 3) &nbsp;·&nbsp;
        MongoDB Atlas MCP Server &nbsp;·&nbsp; Google Cloud Run</p>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);
                  border-radius:12px;padding:10px 16px;text-align:center;backdrop-filter:blur(10px);">
        <div style="color:rgba(255,255,255,0.65);font-size:.68em;font-weight:700;letter-spacing:1px;">TRACK</div>
        <div style="color:white;font-weight:700;font-size:.88em;">MongoDB Partner</div>
      </div>
      <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);
                  border-radius:12px;padding:10px 16px;text-align:center;backdrop-filter:blur(10px);">
        <div style="color:rgba(255,255,255,0.65);font-size:.68em;font-weight:700;letter-spacing:1px;">HACKATHON</div>
        <div style="color:white;font-weight:700;font-size:.88em;">Google Cloud Rapid Agent 2026</div>
      </div>
    </div>
  </div>
</div>"""


def create_ui():
    import gradio as gr

    with gr.Blocks(css=CSS, title=f"RetailPulse AI — {MALL_NAME}",
                   theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate")) as demo:

        gr.HTML(HEADER)

        with gr.Tabs():

            # ══════════════════════════════════════════════════════════════
            # TAB 1 — OVERVIEW DASHBOARD
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("📊 Overview"):
                kpi_display = gr.HTML(
                    "<div style='text-align:center;padding:24px;color:#888;font-size:1.05em;'>"
                    "⏳ Loading live data from MongoDB Atlas...</div>")

                with gr.Row():
                    rev_chart  = gr.Plot(label="Revenue Trend")
                    ff_chart   = gr.Plot(label="Footfall")

                with gr.Row():
                    cat_chart  = gr.Plot(label="Revenue by Category")
                    zone_chart = gr.Plot(label="Revenue by Zone")

                with gr.Row():
                    with gr.Column(scale=3):
                        gr.Markdown("### 🏆 Top Tenants This Week")
                        top_table = gr.Dataframe(
                            headers=["Tenant","Category","Zone",
                                     "Revenue (Week)","vs Last Week","Transactions"],
                            interactive=False)
                    with gr.Column(scale=2):
                        gr.Markdown("### 🚨 Open Alerts")
                        alerts_table = gr.Dataframe(
                            headers=["Severity","Type","Tenant/Zone","Message","Time"],
                            interactive=False, wrap=True)

                gr.Button("🔄 Refresh Dashboard", variant="primary", size="lg").click(
                    fn=load_overview,
                    outputs=[kpi_display, rev_chart, ff_chart, cat_chart,
                             zone_chart, top_table, alerts_table])

                demo.load(fn=load_overview,
                          outputs=[kpi_display, rev_chart, ff_chart, cat_chart,
                                   zone_chart, top_table, alerts_table])

            # ══════════════════════════════════════════════════════════════
            # TAB 2 — ANALYTICS
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("📈 Analytics"):
                gr.Markdown("### Deep-dive analytics — category trends, footfall heatmap, underperformers")

                trend_chart   = gr.Plot(label="Category Revenue Trends")
                with gr.Row():
                    heat_chart    = gr.Plot(label="Footfall Heatmap")
                    ff_trend_chart = gr.Plot(label="Footfall Trend")

                gr.Markdown("### ⚠️ Underperforming Tenants (>15% revenue decline vs last week)")
                underperf_table = gr.Dataframe(
                    headers=["Tenant","Category","Zone","This Week","Last Week","Decline"],
                    interactive=False)

                gr.Button("🔄 Refresh Analytics", variant="primary").click(
                    fn=load_analytics,
                    outputs=[trend_chart, heat_chart, ff_trend_chart, underperf_table])

                demo.load(fn=load_analytics,
                          outputs=[trend_chart, heat_chart, ff_trend_chart, underperf_table])

            # ══════════════════════════════════════════════════════════════
            # TAB 3 — OPERATIONS
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("⚙️ Operations"):
                gr.Markdown("### Alerts, active promotions, and lease expiry tracker")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 🚨 Open Alerts")
                        ops_alerts = gr.Dataframe(
                            headers=["Severity","Type","Tenant/Zone","Message","Time"],
                            interactive=False, wrap=True)
                    with gr.Column():
                        gr.Markdown("#### 🎯 Active Promotions")
                        ops_promos = gr.Dataframe(
                            headers=["Title","Category","Discount","Start","End",
                                     "Expected Lift","Status"],
                            interactive=False)

                gr.Markdown("#### 📋 Lease Expiry Tracker")
                ops_leases = gr.Dataframe(
                    headers=["Tenant","Category","Zone","Lease Ends","Days Left","Status"],
                    interactive=False)

                gr.Button("🔄 Refresh Operations", variant="primary").click(
                    fn=load_operations,
                    outputs=[ops_alerts, ops_promos, ops_leases])

                demo.load(fn=load_operations,
                          outputs=[ops_alerts, ops_promos, ops_leases])

            # ══════════════════════════════════════════════════════════════
            # TAB 4 — AI ASSISTANT
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("🤖 AI Assistant"):
                with gr.Row():
                    # Sidebar
                    with gr.Column(scale=1, min_width=230):
                        gr.Markdown("### ⚡ Quick Actions")
                        gr.Markdown("*One click — full multi-step analysis*")
                        btns = []
                        for label in QUICK_ACTIONS:
                            b = gr.Button(label, variant="secondary", size="sm",
                                          elem_classes=["quick-btn"])
                            btns.append((label, b))

                        gr.Markdown("---")
                        gr.HTML("""
                        <div style="background:linear-gradient(135deg,#f8f9ff,#eef2ff);
                                    border-radius:14px;padding:16px;border:1px solid #c5cae9;">
                          <div style="font-weight:800;color:#1a237e;margin-bottom:10px;font-size:.95em;">
                            🛠️ Tech Stack</div>
                          <div style="font-size:.8em;color:#3949ab;line-height:2;">
                            🤖 <b>Google ADK</b> 1.33<br>
                            ✨ <b>Gemini 2.5 Flash</b><br>
                            🍃 <b>MongoDB Atlas MCP</b><br>
                            ☁️ <b>Google Cloud Run</b><br>
                            🐍 <b>Python</b> 3.12<br>
                            🎨 <b>Gradio</b> 6.x
                          </div>
                          <div style="margin-top:12px;padding-top:10px;border-top:1px solid #c5cae9;">
                            <div style="font-weight:800;color:#1a237e;margin-bottom:6px;font-size:.9em;">
                              🗄️ Live Data</div>
                            <div style="font-size:.78em;color:#3949ab;line-height:1.9;">
                              20 tenants · 8 zones<br>
                              90 days history<br>
                              1,800+ revenue records<br>
                              9,360+ footfall records
                            </div>
                          </div>
                        </div>""")

                    # Chat
                    with gr.Column(scale=3):
                        chatbot = gr.ChatInterface(
                            fn=chat,
                            chatbot=gr.Chatbot(
                                height=520,
                                render_markdown=True,
                                placeholder=(
                                    "<div style='text-align:center;padding:50px 20px;'>"
                                    "<div style='font-size:3.5em;margin-bottom:16px;'>🏬</div>"
                                    "<div style='font-size:1.3em;font-weight:700;color:#1a73e8;'>"
                                    "RetailPulse AI</div>"
                                    "<div style='color:#888;margin-top:8px;font-size:.95em;'>"
                                    "Your autonomous mall intelligence agent.<br>"
                                    "Ask me anything or use Quick Actions →</div>"
                                    "<div style='margin-top:20px;display:flex;gap:8px;"
                                    "justify-content:center;flex-wrap:wrap;'>"
                                    "<span style='background:#e8f0fe;color:#1a73e8;padding:6px 12px;"
                                    "border-radius:20px;font-size:.82em;'>📊 Revenue Analysis</span>"
                                    "<span style='background:#e6f4ea;color:#137333;padding:6px 12px;"
                                    "border-radius:20px;font-size:.82em;'>🚨 Anomaly Detection</span>"
                                    "<span style='background:#fce8e6;color:#c5221f;padding:6px 12px;"
                                    "border-radius:20px;font-size:.82em;'>💡 Promotion Planning</span>"
                                    "</div></div>"),
                                avatar_images=(
                                    None,
                                    "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg"),
                            ),
                            textbox=gr.Textbox(
                                placeholder="Ask anything: 'Which tenants are underperforming?' or 'Run anomaly scan'...",
                                container=False, scale=7),
                            examples=[
                                "Which tenants had the highest revenue this week?",
                                "Run the daily anomaly scan and log any issues found",
                                "Find underperforming tenants and create a promotion plan",
                                "Compare this month's revenue to last month by category",
                                "Which zones have the lowest footfall and why?",
                                "Generate a weekly summary report and save it",
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
