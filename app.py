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

    def card(gradient, icon, label, value, sub, sub_col="#94a3b8", glow="rgba(59,130,246,0.3)"):
        return f"""
        <div style="flex:1;min-width:160px;background:{gradient};
                    border-radius:16px;padding:20px 22px;
                    border:1px solid rgba(255,255,255,0.06);
                    box-shadow:0 8px 24px {glow};
                    transition:transform .2s,box-shadow .2s;cursor:default;"
             onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 16px 32px {glow}'"
             onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 8px 24px {glow}'">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="font-size:.68em;font-weight:700;letter-spacing:1.2px;
                        color:rgba(255,255,255,0.55);text-transform:uppercase;">{label}</div>
            <div style="font-size:1.4em;opacity:.8;">{icon}</div>
          </div>
          <div style="font-size:2em;font-weight:800;color:#f1f5f9;margin:8px 0 4px 0;
                      letter-spacing:-.5px;">{value}</div>
          <div style="font-size:.78em;color:{sub_col};font-weight:500;">{sub}</div>
        </div>"""

    return f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;padding:20px 24px 8px 24px;">
      {card("linear-gradient(135deg,#1e3a5f,#1d4ed8)", "💰", "Today's Revenue",
            f"${kpis.get('today_revenue',0):,.0f}",
            f"{ra} {abs(rc):.1f}% vs yesterday", rc_col, "rgba(29,78,216,0.4)")}
      {card("linear-gradient(135deg,#14532d,#16a34a)", "👣", "Today's Footfall",
            f"{kpis.get('today_footfall',0):,}",
            f"{fa} {abs(fc):.1f}% vs yesterday", fc_col, "rgba(22,163,74,0.4)")}
      {card("linear-gradient(135deg,#3b0764,#7c3aed)", "📅", "Week Revenue",
            f"${kpis.get('week_revenue',0):,.0f}",
            f"{wa} {abs(wc):.1f}% vs last week", wc_col, "rgba(124,58,237,0.4)")}
      {card("linear-gradient(135deg,#7c1d1d,#dc2626)" if al > 0 else "linear-gradient(135deg,#14532d,#16a34a)",
            "🚨" if al > 0 else "✅", "Open Alerts",
            str(al),
            "Needs attention" if al > 0 else "All clear",
            "#fca5a5" if al > 0 else "#86efac",
            "rgba(220,38,38,0.4)" if al > 0 else "rgba(22,163,74,0.4)")}
      {card("linear-gradient(135deg,#831843,#db2777)", "🎯", "Active Promos",
            str(kpis.get('active_promotions',0)),
            f"{kpis.get('total_tenants',0)} tenants total", "#f9a8d4", "rgba(219,39,119,0.4)")}
      {card("linear-gradient(135deg,#164e63,#0891b2)", "📊", "Month Revenue",
            f"${kpis.get('month_revenue',0):,.0f}",
            "Month to date", "#67e8f9", "rgba(8,145,178,0.4)")}
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

    DARK_BG = "#13151f"
    DARK_PANEL = "#1a1d27"
    GRID = "#1e2130"

    # Revenue trend (30 days)
    dates, revenues = get_revenue_chart_data(30)
    rev_fig = go.Figure()
    if dates:
        rev_fig.add_trace(go.Scatter(
            x=dates, y=revenues, mode="lines+markers",
            line=dict(color="#60a5fa", width=2.5),
            marker=dict(size=5, color="#60a5fa", line=dict(color=DARK_BG, width=2)),
            fill="tozeroy", fillcolor="rgba(96,165,250,0.08)",
            hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>"))
    rev_fig.update_layout(
        title=dict(text="📈 30-Day Revenue Trend", font=dict(size=13, color="#94a3b8")),
        height=260, plot_bgcolor=DARK_PANEL, paper_bgcolor=DARK_PANEL,
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor=GRID,
                   color="#64748b", zeroline=False),
        xaxis=dict(gridcolor=GRID, color="#64748b", tickangle=-30),
        margin=dict(l=60, r=16, t=40, b=50), hovermode="x unified",
        showlegend=False, font=dict(color="#94a3b8"))

    # Hourly footfall
    hours, counts = get_footfall_chart_data()
    ff_fig = go.Figure()
    if hours and counts:
        max_v = max(counts) if counts else 1
        colors = ["#f87171" if c == max_v else "#34d399" if c == min(counts) else "#60a5fa"
                  for c in counts]
        ff_fig.add_trace(go.Bar(x=hours, y=counts, marker_color=colors,
                                hovertemplate="<b>%{x}</b><br>%{y:,} visitors<extra></extra>"))
    ff_fig.update_layout(
        title=dict(text="👣 Today's Hourly Footfall", font=dict(size=13, color="#94a3b8")),
        height=260, plot_bgcolor=DARK_PANEL, paper_bgcolor=DARK_PANEL,
        yaxis=dict(gridcolor=GRID, color="#64748b", zeroline=False),
        xaxis=dict(gridcolor=GRID, color="#64748b"),
        margin=dict(l=40, r=16, t=40, b=40), showlegend=False,
        font=dict(color="#94a3b8"))

    # Category donut
    cats, cat_revs = get_category_revenue_data()
    cat_fig = go.Figure()
    if cats:
        cat_fig.add_trace(go.Pie(
            labels=cats, values=cat_revs, hole=0.55,
            textinfo="label+percent",
            marker=dict(colors=["#60a5fa","#34d399","#f59e0b","#a78bfa",
                                 "#f87171","#22d3ee","#fb923c","#94a3b8"],
                        line=dict(color=DARK_BG, width=2)),
            textfont=dict(size=11, color="#e2e8f0"),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>"))
    cat_fig.update_layout(
        title=dict(text="🏷️ Revenue by Category", font=dict(size=13, color="#94a3b8")),
        height=260, margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False, paper_bgcolor=DARK_PANEL, font=dict(color="#94a3b8"))

    # Zone bar
    zones, zone_revs = get_zone_revenue_data()
    zone_fig = go.Figure()
    if zones:
        zone_fig.add_trace(go.Bar(
            x=zones, y=zone_revs,
            marker=dict(color=zone_revs, colorscale=[[0,"#1e3a5f"],[1,"#60a5fa"]],
                        showscale=False, line=dict(color=DARK_BG, width=1)),
            hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>"))
    zone_fig.update_layout(
        title=dict(text="🗺️ Revenue by Zone (This Month)", font=dict(size=13, color="#94a3b8")),
        height=260, plot_bgcolor=DARK_PANEL, paper_bgcolor=DARK_PANEL,
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor=GRID,
                   color="#64748b", zeroline=False),
        xaxis=dict(color="#64748b"),
        margin=dict(l=60, r=16, t=40, b=40), showlegend=False,
        font=dict(color="#94a3b8"))

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

    DARK_BG = "#13151f"
    DARK_PANEL = "#1a1d27"
    GRID = "#1e2130"

    # Category trend lines
    cat_trends = get_revenue_by_category_trend(30)
    trend_fig = go.Figure()
    colors = ["#60a5fa","#34d399","#f59e0b","#a78bfa",
              "#f87171","#22d3ee","#fb923c","#94a3b8"]
    for i, (cat, (dates, revs)) in enumerate(cat_trends.items()):
        trend_fig.add_trace(go.Scatter(
            x=dates, y=revs, mode="lines", name=cat,
            line=dict(color=colors[i % len(colors)], width=2.5),
            hovertemplate=f"<b>{cat}</b><br>%{{x}}<br>$%{{y:,.0f}}<extra></extra>"))
    trend_fig.update_layout(
        title=dict(text="📊 Revenue by Category — 30-Day Trend",
                   font=dict(size=13, color="#94a3b8")),
        height=320, plot_bgcolor=DARK_PANEL, paper_bgcolor=DARK_PANEL,
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor=GRID,
                   color="#64748b"),
        xaxis=dict(gridcolor=GRID, color="#64748b", tickangle=-30),
        margin=dict(l=60, r=20, t=40, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified", font=dict(color="#94a3b8"))

    # Footfall heatmap
    zones, hours, matrix = get_footfall_heatmap_data()
    heat_fig = go.Figure()
    if zones and hours and matrix:
        heat_fig.add_trace(go.Heatmap(
            z=matrix, x=hours, y=zones,
            colorscale=[[0, "#1e2130"], [0.5, "#1d4ed8"], [1, "#f59e0b"]],
            hovertemplate="<b>%{y}</b> at %{x}<br>Avg: %{z:,.0f} visitors<extra></extra>",
            colorbar=dict(title="Visitors", tickfont=dict(color="#94a3b8"),
                          titlefont=dict(color="#94a3b8"))))
    heat_fig.update_layout(
        title=dict(text="🔥 Footfall Heatmap — Zone × Hour (7-Day Avg)",
                   font=dict(size=13, color="#94a3b8")),
        height=320, paper_bgcolor=DARK_PANEL,
        xaxis=dict(title="Hour", color="#64748b", gridcolor=GRID),
        yaxis=dict(title="Zone", color="#64748b"),
        margin=dict(l=80, r=20, t=40, b=60), font=dict(color="#94a3b8"))

    # Weekly footfall trend
    ff_dates, ff_counts = get_weekly_footfall_trend()
    ff_trend_fig = go.Figure()
    if ff_dates:
        ff_trend_fig.add_trace(go.Scatter(
            x=ff_dates, y=ff_counts, mode="lines+markers",
            line=dict(color="#34d399", width=2.5),
            marker=dict(size=6, color="#34d399", line=dict(color=DARK_BG, width=2)),
            fill="tozeroy", fillcolor="rgba(52,211,153,0.08)",
            hovertemplate="<b>%{x}</b><br>%{y:,} visitors<extra></extra>"))
    ff_trend_fig.update_layout(
        title=dict(text="👣 14-Day Footfall Trend", font=dict(size=13, color="#94a3b8")),
        height=280, plot_bgcolor=DARK_PANEL, paper_bgcolor=DARK_PANEL,
        yaxis=dict(gridcolor=GRID, color="#64748b", zeroline=False),
        xaxis=dict(gridcolor=GRID, color="#64748b", tickangle=-30),
        margin=dict(l=50, r=16, t=40, b=50), showlegend=False,
        hovermode="x unified", font=dict(color="#94a3b8"))

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
/* ── Reset Gradio's bland defaults ── */
body, .gradio-container {
    background: #0f1117 !important;
    font-family: 'Google Sans', 'Inter', -apple-system, sans-serif !important;
}
.gradio-container {
    max-width: 1440px !important;
    margin: 0 auto !important;
    padding: 0 !important;
}
footer { display: none !important; }

/* ── Tabs ── */
.tab-nav {
    background: #1a1d27 !important;
    border-bottom: 1px solid #2d3142 !important;
    padding: 0 24px !important;
    position: sticky !important;
    top: 0 !important;
    z-index: 100 !important;
}
.tab-nav button {
    color: #8b92a5 !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 14px 20px !important;
    border-radius: 0 !important;
    border-bottom: 3px solid transparent !important;
    background: transparent !important;
    transition: all .2s !important;
}
.tab-nav button:hover { color: #e2e8f0 !important; }
.tab-nav button.selected {
    color: #60a5fa !important;
    border-bottom: 3px solid #60a5fa !important;
    background: transparent !important;
}

/* ── Main content area ── */
.tabitem, .tab-content, .block {
    background: transparent !important;
    border: none !important;
}
.gap, .contain {
    background: transparent !important;
}

/* ── Cards / panels ── */
.panel, .form {
    background: #1a1d27 !important;
    border: 1px solid #2d3142 !important;
    border-radius: 12px !important;
}

/* ── Dataframes ── */
.table-wrap, table {
    background: #1a1d27 !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
thead tr { background: #252836 !important; }
thead th {
    color: #94a3b8 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: .8px !important;
    text-transform: uppercase !important;
    padding: 10px 14px !important;
    border-bottom: 1px solid #2d3142 !important;
}
tbody tr { border-bottom: 1px solid #1e2130 !important; }
tbody tr:hover { background: #252836 !important; }
tbody td {
    color: #cbd5e1 !important;
    padding: 10px 14px !important;
    font-size: 13px !important;
}

/* ── Buttons ── */
button.primary, .gr-button-primary {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    box-shadow: 0 4px 12px rgba(59,130,246,0.4) !important;
    transition: all .2s !important;
}
button.primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 16px rgba(59,130,246,0.5) !important;
}
button.secondary {
    background: #1e2130 !important;
    border: 1px solid #2d3142 !important;
    color: #94a3b8 !important;
    font-size: 12px !important;
    border-radius: 8px !important;
    text-align: left !important;
    transition: all .15s !important;
}
button.secondary:hover {
    background: #252836 !important;
    border-color: #3b82f6 !important;
    color: #60a5fa !important;
}

/* ── Textbox / input ── */
textarea, input[type=text] {
    background: #1e2130 !important;
    border: 1px solid #2d3142 !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
    font-size: 14px !important;
}
textarea:focus, input[type=text]:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}

/* ── Chatbot ── */
.chatbot {
    background: #13151f !important;
    border: 1px solid #2d3142 !important;
    border-radius: 12px !important;
}
.message.user .bubble-wrap .message-bubble-border {
    background: linear-gradient(135deg, #1d4ed8, #3b82f6) !important;
    border-radius: 18px 18px 4px 18px !important;
}
.message.bot .bubble-wrap .message-bubble-border {
    background: #1e2130 !important;
    border: 1px solid #2d3142 !important;
    border-radius: 18px 18px 18px 4px !important;
}

/* ── Markdown text ── */
.prose, p, span, label, .label-wrap {
    color: #cbd5e1 !important;
}
h1, h2, h3, h4 { color: #e2e8f0 !important; }

/* ── Plots ── */
.plot-container { border-radius: 12px !important; overflow: hidden !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #13151f; }
::-webkit-scrollbar-thumb { background: #2d3142; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3b82f6; }
"""

HEADER = f"""
<div style="background:linear-gradient(135deg,#0f1117 0%,#1a1d27 100%);
            padding:0;margin:0;border-bottom:1px solid #2d3142;">
  <div style="background:linear-gradient(90deg,#1d4ed8 0%,#3b82f6 50%,#06b6d4 100%);
              height:3px;width:100%;"></div>
  <div style="padding:20px 32px 18px 32px;display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
    <div style="display:flex;align-items:center;gap:14px;">
      <div style="width:44px;height:44px;background:linear-gradient(135deg,#3b82f6,#06b6d4);
                  border-radius:12px;display:flex;align-items:center;justify-content:center;
                  font-size:1.5em;box-shadow:0 4px 12px rgba(59,130,246,0.4);">🏬</div>
      <div>
        <div style="font-size:1.4em;font-weight:800;color:#f1f5f9;letter-spacing:-.3px;
                    background:linear-gradient(90deg,#60a5fa,#22d3ee);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
          RetailPulse AI</div>
        <div style="font-size:.78em;color:#64748b;margin-top:1px;">
          Autonomous Mall Intelligence &nbsp;·&nbsp; <span style="color:#94a3b8;">{MALL_NAME}</span></div>
      </div>
    </div>
    <div style="flex:1;"></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <span style="background:#1e2130;border:1px solid #2d3142;border-radius:20px;
                   padding:5px 12px;font-size:.72em;color:#60a5fa;font-weight:600;">
        ✦ Google ADK</span>
      <span style="background:#1e2130;border:1px solid #2d3142;border-radius:20px;
                   padding:5px 12px;font-size:.72em;color:#34d399;font-weight:600;">
        ✦ Gemini 2.5 Flash</span>
      <span style="background:#1e2130;border:1px solid #2d3142;border-radius:20px;
                   padding:5px 12px;font-size:.72em;color:#f59e0b;font-weight:600;">
        ✦ MongoDB Atlas MCP</span>
      <span style="background:#1e2130;border:1px solid #2d3142;border-radius:20px;
                   padding:5px 12px;font-size:.72em;color:#a78bfa;font-weight:600;">
        ✦ Cloud Run</span>
      <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);border-radius:8px;
                  padding:6px 14px;font-size:.72em;color:white;font-weight:700;
                  box-shadow:0 2px 8px rgba(59,130,246,0.4);">
        MongoDB Partner Track</div>
    </div>
  </div>
</div>"""


def create_ui():
    import gradio as gr

    with gr.Blocks(title=f"RetailPulse AI — {MALL_NAME}") as demo:

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
                        <div style="background:#13151f;border:1px solid #2d3142;
                                    border-radius:14px;padding:16px;margin-top:8px;">
                          <div style="font-weight:700;color:#60a5fa;margin-bottom:10px;
                                      font-size:.85em;letter-spacing:.5px;">🛠️ TECH STACK</div>
                          <div style="font-size:.78em;line-height:2.2;">
                            <div style="color:#94a3b8;">🤖 <span style="color:#e2e8f0;font-weight:600;">Google ADK</span> 1.33</div>
                            <div style="color:#94a3b8;">✨ <span style="color:#e2e8f0;font-weight:600;">Gemini 2.5 Flash</span></div>
                            <div style="color:#94a3b8;">🍃 <span style="color:#e2e8f0;font-weight:600;">MongoDB Atlas MCP</span></div>
                            <div style="color:#94a3b8;">☁️ <span style="color:#e2e8f0;font-weight:600;">Google Cloud Run</span></div>
                            <div style="color:#94a3b8;">🐍 <span style="color:#e2e8f0;font-weight:600;">Python</span> 3.12</div>
                          </div>
                          <div style="margin-top:12px;padding-top:10px;border-top:1px solid #2d3142;">
                            <div style="font-weight:700;color:#34d399;margin-bottom:8px;
                                        font-size:.85em;letter-spacing:.5px;">🗄️ LIVE DATA</div>
                            <div style="font-size:.75em;color:#64748b;line-height:2;">
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
                                    "<div style='text-align:center;padding:50px 20px;"
                                    "background:#13151f;border-radius:12px;'>"
                                    "<div style='font-size:3em;margin-bottom:12px;'>🏬</div>"
                                    "<div style='font-size:1.2em;font-weight:700;"
                                    "background:linear-gradient(90deg,#60a5fa,#22d3ee);"
                                    "-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>"
                                    "RetailPulse AI</div>"
                                    "<div style='color:#64748b;margin-top:8px;font-size:.9em;'>"
                                    "Autonomous mall intelligence.<br>"
                                    "Ask anything or use Quick Actions →</div>"
                                    "<div style='margin-top:16px;display:flex;gap:8px;"
                                    "justify-content:center;flex-wrap:wrap;'>"
                                    "<span style='background:#1e2130;color:#60a5fa;padding:5px 12px;"
                                    "border-radius:20px;font-size:.78em;border:1px solid #2d3142;'>📊 Revenue</span>"
                                    "<span style='background:#1e2130;color:#34d399;padding:5px 12px;"
                                    "border-radius:20px;font-size:.78em;border:1px solid #2d3142;'>🚨 Anomalies</span>"
                                    "<span style='background:#1e2130;color:#f59e0b;padding:5px 12px;"
                                    "border-radius:20px;font-size:.78em;border:1px solid #2d3142;'>💡 Promotions</span>"
                                    "</div></div>"),
                                avatar_images=(
                                    None,
                                    "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg"),
                            ),
                            textbox=gr.Textbox(
                                placeholder="Ask anything: 'Which tenants are underperforming?' or 'Run anomaly scan'...",
                                container=False, scale=7, submit_btn="Send ➤"),
                            examples=[
                                "Which tenants had the highest revenue this week?",
                                "Run the daily anomaly scan and log any issues found",
                                "Find underperforming tenants and create a promotion plan",
                                "Compare this month's revenue to last month by category",
                                "Which zones have the lowest footfall and why?",
                                "Generate a weekly summary report and save it",
                            ],
                        )

                for label, btn in btns:
                    query = QUICK_ACTIONS[label]
                    btn.click(lambda q=query: q, outputs=chatbot.textbox)

    return demo


if __name__ == "__main__":
    import gradio as gr
    print(f"\n🏬 RetailPulse AI — {MALL_NAME}")
    print(f"   Port: {PORT}\n")
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=PORT,
        css=CSS,
        theme=gr.themes.Base(
            primary_hue="blue",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
    )
