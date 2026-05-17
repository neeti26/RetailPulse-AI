"""
RetailPulse AI — Gradio Web UI
Tabs: Dashboard (live charts) + AI Assistant (agent chat)

Run with: python app.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

MALL_NAME = os.getenv("MALL_NAME", "Sunrise Mall")
# Cloud Run sets PORT env var — respect it, fall back to UI_PORT
UI_PORT = int(os.getenv("PORT", os.getenv("UI_PORT", "7860")))

# ─────────────────────────────────────────────────────────────────────────────
# Agent — lazy-loaded on first message, not at startup
# ─────────────────────────────────────────────────────────────────────────────
_runner = None
_session_service = None
_session_id = None
_agent_loop = None
_agent_error = None  # stores init error to show in UI


def _get_runner():
    """Lazy-initialize the ADK runner with a dedicated event loop."""
    global _runner, _session_service, _session_id, _agent_loop, _agent_error

    if _runner is not None:
        return _runner, _session_service, _session_id

    if _agent_error is not None:
        raise RuntimeError(_agent_error)

    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from retailpulse.agent import root_agent

        _agent_loop = asyncio.new_event_loop()
        _session_service = InMemorySessionService()
        _runner = Runner(
            agent=root_agent,
            app_name="retailpulse_ui",
            session_service=_session_service,
        )

        async def _create_session():
            session = await _session_service.create_session(
                app_name="retailpulse_ui",
                user_id="mall_manager",
            )
            return session.id

        _session_id = _agent_loop.run_until_complete(_create_session())
        return _runner, _session_service, _session_id

    except Exception as e:
        _agent_error = str(e)
        raise


def run_agent(user_message: str, history: list) -> Generator:
    """Run the agent and yield the final response."""
    from google.genai import types as genai_types

    runner, session_service, session_id = _get_runner()

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)],
    )

    full_response = ""

    async def _run():
        nonlocal full_response
        async for event in runner.run_async(
            user_id="mall_manager",
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            full_response += part.text

    try:
        _agent_loop.run_until_complete(_run())
    except Exception as e:
        full_response = (
            f"⚠️ Agent error: {e}\n\n"
            "Please check your MongoDB connection and API key in `.env`."
        )

    yield full_response or "No response received. Please try again."


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard data helpers
# ─────────────────────────────────────────────────────────────────────────────
def _arrow(change: float) -> str:
    if change > 0:
        return f"↑ +{change:.1f}%"
    elif change < 0:
        return f"↓ {change:.1f}%"
    return "→ 0%"


def _color(change: float) -> str:
    return "green" if change >= 0 else "red"


def load_dashboard():
    """Fetch all dashboard data and return Gradio component updates."""
    import plotly.graph_objects as go
    from retailpulse.dashboard import (
        get_kpi_cards,
        get_revenue_chart_data,
        get_footfall_chart_data,
        get_top_tenants_table,
        get_active_alerts_table,
        get_category_revenue_data,
    )

    kpis = get_kpi_cards()

    # ── KPI card HTML ────────────────────────────────────────────────────────
    rev_arrow = _arrow(kpis["today_revenue_change"])
    ff_arrow = _arrow(kpis["today_footfall_change"])
    rev_color = _color(kpis["today_revenue_change"])
    ff_color = _color(kpis["today_footfall_change"])

    kpi_html = f"""
    <div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:8px;">
      <div style="flex:1; min-width:140px; background:#f0f7ff; border-radius:12px;
                  padding:16px; border-left:4px solid #1a73e8;">
        <div style="font-size:0.8em; color:#555; font-weight:600;">TODAY'S REVENUE</div>
        <div style="font-size:1.8em; font-weight:700; color:#1a1a1a;">
          ${kpis['today_revenue']:,.0f}
        </div>
        <div style="font-size:0.85em; color:{rev_color};">{rev_arrow} vs yesterday</div>
      </div>
      <div style="flex:1; min-width:140px; background:#f0fff4; border-radius:12px;
                  padding:16px; border-left:4px solid #34a853;">
        <div style="font-size:0.8em; color:#555; font-weight:600;">TODAY'S FOOTFALL</div>
        <div style="font-size:1.8em; font-weight:700; color:#1a1a1a;">
          {kpis['today_footfall']:,}
        </div>
        <div style="font-size:0.85em; color:{ff_color};">{ff_arrow} vs yesterday</div>
      </div>
      <div style="flex:1; min-width:140px; background:#fff8f0; border-radius:12px;
                  padding:16px; border-left:4px solid #fa7b17;">
        <div style="font-size:0.8em; color:#555; font-weight:600;">OPEN ALERTS</div>
        <div style="font-size:1.8em; font-weight:700;
                    color:{'#d93025' if kpis['active_alerts'] > 0 else '#1a1a1a'};">
          {kpis['active_alerts']}
        </div>
        <div style="font-size:0.85em; color:#888;">unresolved issues</div>
      </div>
      <div style="flex:1; min-width:140px; background:#f8f0ff; border-radius:12px;
                  padding:16px; border-left:4px solid #9334e6;">
        <div style="font-size:0.8em; color:#555; font-weight:600;">ACTIVE PROMOS</div>
        <div style="font-size:1.8em; font-weight:700; color:#1a1a1a;">
          {kpis['active_promotions']}
        </div>
        <div style="font-size:0.85em; color:#888;">{kpis['total_tenants']} total tenants</div>
      </div>
    </div>
    """

    # ── Revenue trend chart ──────────────────────────────────────────────────
    dates, revenues = get_revenue_chart_data()
    if dates:
        rev_fig = go.Figure()
        rev_fig.add_trace(go.Scatter(
            x=dates, y=revenues,
            mode="lines+markers",
            line=dict(color="#1a73e8", width=2.5),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(26,115,232,0.08)",
            name="Revenue",
        ))
        rev_fig.update_layout(
            title="14-Day Revenue Trend",
            xaxis_title="Date",
            yaxis_title="Revenue ($)",
            margin=dict(l=40, r=20, t=40, b=40),
            height=280,
            plot_bgcolor="white",
            paper_bgcolor="white",
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
        )
    else:
        rev_fig = go.Figure()
        rev_fig.update_layout(
            title="14-Day Revenue Trend (no data — run seed_data.py)",
            height=280,
        )

    # ── Hourly footfall chart ────────────────────────────────────────────────
    hours, counts = get_footfall_chart_data()
    if hours:
        ff_fig = go.Figure()
        ff_fig.add_trace(go.Bar(
            x=hours, y=counts,
            marker_color="#34a853",
            name="Visitors",
        ))
        ff_fig.update_layout(
            title="Today's Hourly Footfall by Zone",
            xaxis_title="Hour",
            yaxis_title="Visitors",
            margin=dict(l=40, r=20, t=40, b=40),
            height=280,
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
    else:
        ff_fig = go.Figure()
        ff_fig.update_layout(
            title="Hourly Footfall (no data — run seed_data.py)",
            height=280,
        )

    # ── Category revenue pie chart ───────────────────────────────────────────
    categories, cat_revenues = get_category_revenue_data()
    if categories:
        cat_fig = go.Figure(go.Pie(
            labels=categories,
            values=cat_revenues,
            hole=0.4,
            textinfo="label+percent",
            marker=dict(colors=[
                "#1a73e8", "#34a853", "#fa7b17", "#9334e6",
                "#d93025", "#00bcd4", "#ff9800", "#607d8b",
            ]),
        ))
        cat_fig.update_layout(
            title="Revenue by Category (This Month)",
            margin=dict(l=20, r=20, t=40, b=20),
            height=280,
            showlegend=False,
        )
    else:
        cat_fig = go.Figure()
        cat_fig.update_layout(
            title="Revenue by Category (no data)",
            height=280,
        )

    # ── Tables ───────────────────────────────────────────────────────────────
    top_tenants = get_top_tenants_table()
    alerts = get_active_alerts_table()

    return (
        kpi_html,
        rev_fig,
        ff_fig,
        cat_fig,
        top_tenants if top_tenants else [{"Info": "No data — run scripts/seed_data.py"}],
        alerts if alerts else [{"Info": "No open alerts 🎉"}],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Quick Actions for the chat tab
# ─────────────────────────────────────────────────────────────────────────────
QUICK_ACTIONS = {
    "🔍 Top Performers": (
        "Show me the top 5 tenants by revenue this week, "
        "with percentage change vs last week."
    ),
    "🚨 Anomaly Scan": (
        "Run a full anomaly scan: check for revenue drops >20%, footfall drops >25%, "
        "zero-activity tenants, and leases expiring within 60 days. Log any issues found."
    ),
    "📊 Weekly Report": (
        "Generate a comprehensive weekly summary report for this week. Include total "
        "revenue, footfall, top performers, underperformers, and key insights. "
        "Save it to the database."
    ),
    "💡 Promotion Plan": (
        "Identify the 3 most underperforming tenants this month and create a targeted "
        "promotion plan for each. Save the plans to the promotions collection."
    ),
    "👣 Footfall Heatmap": (
        "Show me the hourly footfall breakdown by zone for yesterday. "
        "Which zones and hours had the highest and lowest traffic?"
    ),
    "📋 Active Alerts": (
        "Show me all unresolved alerts, sorted by severity. "
        "What actions do you recommend for each?"
    ),
    "🏪 Tenant Overview": (
        "Give me a full overview of all tenants: their categories, zones, "
        "current month revenue, and lease status."
    ),
    "📈 Revenue Trends": (
        "Show me revenue trends for the last 30 days. "
        "Which categories are growing and which are declining?"
    ),
}

WELCOME_MESSAGE = f"""Welcome to **RetailPulse AI** — your intelligent operations assistant for **{MALL_NAME}**! 🏬

I can help you:
- 📊 **Analyze** tenant revenue and footfall trends
- 🚨 **Detect** anomalies and operational issues proactively
- 💡 **Plan** targeted promotions for underperforming tenants
- 📋 **Generate** daily and weekly summary reports
- 🏪 **Manage** tenant data and operational alerts

Use the **Quick Actions** on the left, or ask me anything in natural language.

*Try: "Which tenants had the worst performance this week?"*
"""

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
.gradio-container { max-width: 1280px !important; margin: 0 auto !important; }
#chatbot { height: 560px; }
footer { display: none !important; }
.kpi-html { margin-bottom: 4px; }
.tab-nav button { font-size: 15px !important; font-weight: 600 !important; }
"""

HEADER_HTML = f"""
<div style="text-align:center; padding:18px 0 10px 0; border-bottom:1px solid #e8eaed; margin-bottom:12px;">
  <h1 style="font-size:2em; margin:0; color:#1a73e8; font-weight:700;">
    🏬 RetailPulse AI
  </h1>
  <p style="font-size:1em; color:#555; margin:6px 0 0 0;">
    Smart Mall Intelligence Agent &nbsp;·&nbsp; <strong>{MALL_NAME}</strong>
  </p>
  <p style="font-size:0.82em; color:#999; margin:4px 0 0 0;">
    Google ADK &nbsp;·&nbsp; Gemini 2.5 Flash (Gemini 3) &nbsp;·&nbsp;
    MongoDB Atlas MCP &nbsp;·&nbsp; Google Cloud Run
  </p>
</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Build UI
# ─────────────────────────────────────────────────────────────────────────────
def create_ui():
    import gradio as gr
    import plotly.graph_objects as go

    with gr.Blocks(
        css=CSS,
        title=f"RetailPulse AI — {MALL_NAME}",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="slate"),
    ) as demo:

        gr.HTML(HEADER_HTML)

        with gr.Tabs():

            # ══════════════════════════════════════════════════════════════
            # TAB 1 — LIVE DASHBOARD
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("📊 Live Dashboard"):

                kpi_display = gr.HTML(
                    value="<p style='color:#888'>Click <b>Refresh Dashboard</b> to load live data.</p>",
                    elem_classes=["kpi-html"],
                )

                with gr.Row():
                    rev_chart = gr.Plot(label="Revenue Trend")
                    ff_chart = gr.Plot(label="Footfall")

                with gr.Row():
                    cat_chart = gr.Plot(label="Revenue by Category")
                    with gr.Column():
                        gr.Markdown("#### 🚨 Open Alerts")
                        alerts_table = gr.Dataframe(
                            headers=["Severity", "Type", "Tenant/Zone", "Message", "Time"],
                            datatype=["str", "str", "str", "str", "str"],
                            interactive=False,
                            wrap=True,
                        )

                gr.Markdown("#### 🏆 Top Tenants This Week")
                top_table = gr.Dataframe(
                    headers=["Tenant", "Category", "Zone", "Revenue (Week)", "Transactions"],
                    datatype=["str", "str", "str", "str", "number"],
                    interactive=False,
                )

                refresh_btn = gr.Button(
                    "🔄 Refresh Dashboard",
                    variant="primary",
                    size="lg",
                )

                refresh_btn.click(
                    fn=load_dashboard,
                    outputs=[kpi_display, rev_chart, ff_chart, cat_chart, top_table, alerts_table],
                )

                # Auto-load on tab open
                demo.load(
                    fn=load_dashboard,
                    outputs=[kpi_display, rev_chart, ff_chart, cat_chart, top_table, alerts_table],
                )

            # ══════════════════════════════════════════════════════════════
            # TAB 2 — AI ASSISTANT
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("🤖 AI Assistant"):

                with gr.Row():

                    # ── Left: Quick Actions ──────────────────────────────
                    with gr.Column(scale=1, min_width=210):
                        gr.Markdown("### ⚡ Quick Actions")
                        gr.Markdown(
                            "*One click to run a full analysis.*",
                            elem_classes=["quick-action-desc"],
                        )

                        action_buttons = []
                        for label in QUICK_ACTIONS:
                            btn = gr.Button(label, variant="secondary", size="sm")
                            action_buttons.append((label, btn))

                        gr.Markdown("---")
                        gr.Markdown("### ℹ️ Stack")
                        gr.Markdown(
                            "**Track:** MongoDB Partner  \n"
                            "**Agent:** Google ADK  \n"
                            "**Model:** Gemini 2.5 Flash  \n"
                            "**DB:** MongoDB Atlas  \n"
                            "**MCP:** mongodb-mcp-server  \n"
                            "**Host:** Google Cloud Run  \n"
                        )

                    # ── Right: Chat ──────────────────────────────────────
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            value=[[None, WELCOME_MESSAGE]],
                            elem_id="chatbot",
                            bubble_full_width=False,
                            show_label=False,
                            render_markdown=True,
                            avatar_images=(
                                None,
                                "https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg",
                            ),
                        )

                        with gr.Row():
                            msg_input = gr.Textbox(
                                placeholder="Ask anything about mall operations...",
                                show_label=False,
                                scale=5,
                                container=False,
                                autofocus=True,
                            )
                            send_btn = gr.Button("Send ➤", variant="primary", scale=1, min_width=80)

                        with gr.Row():
                            clear_btn = gr.Button("🗑️ Clear Chat", size="sm", variant="secondary")
                            gr.Markdown(
                                "*Live MongoDB data · Responses take 10–30s for complex queries*",
                            )

                # ── Event handlers ───────────────────────────────────────
                def user_submit(message, history):
                    if not message.strip():
                        return "", history
                    return "", history + [[message, None]]

                def bot_respond(history):
                    if not history or history[-1][1] is not None:
                        return history
                    user_message = history[-1][0]
                    history[-1][1] = "⏳ Analyzing data..."
                    yield history
                    for chunk in run_agent(user_message, history[:-1]):
                        history[-1][1] = chunk
                        yield history

                send_btn.click(
                    user_submit,
                    inputs=[msg_input, chatbot],
                    outputs=[msg_input, chatbot],
                    queue=False,
                ).then(bot_respond, inputs=[chatbot], outputs=[chatbot])

                msg_input.submit(
                    user_submit,
                    inputs=[msg_input, chatbot],
                    outputs=[msg_input, chatbot],
                    queue=False,
                ).then(bot_respond, inputs=[chatbot], outputs=[chatbot])

                clear_btn.click(
                    lambda: [[None, WELCOME_MESSAGE]],
                    outputs=[chatbot],
                )

                for label, btn in action_buttons:
                    query = QUICK_ACTIONS[label]

                    def make_handler(q):
                        def handler(history):
                            return history + [[q, None]]
                        return handler

                    btn.click(
                        make_handler(query),
                        inputs=[chatbot],
                        outputs=[chatbot],
                        queue=False,
                    ).then(bot_respond, inputs=[chatbot], outputs=[chatbot])

    return demo


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import gradio as gr  # noqa: F401 — verify gradio importable before launch

    print(f"\n🏬 RetailPulse AI — {MALL_NAME}")
    print(f"   MongoDB : {os.getenv('MONGODB_URI', 'mongodb://localhost:27017/retailpulse')}")
    print(f"   Model   : {os.getenv('AGENT_MODEL', 'gemini-2.5-flash')}")
    print(f"   Port    : {UI_PORT}")
    print(f"\n   Open http://localhost:{UI_PORT}\n")

    demo = create_ui()
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=UI_PORT,
        share=False,
        show_error=True,
    )