"""
AI-Augmented Operations Dashboard
Python + Streamlit + Anthropic Claude API

A live dashboard for marketing & operations metrics that layers LLM-generated
narrative insights, anomaly detection, and report drafting on top of the raw
charts — so the person reading it gets the "so what," not just the numbers.

Run:
    streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

import ai_engine
import data_utils as du

load_dotenv()  # pulls ANTHROPIC_API_KEY from a local .env file if present

st.set_page_config(
    page_title="AI-Augmented Operations Dashboard",
    page_icon="📊",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Sidebar: filters + API key handling
# ----------------------------------------------------------------------------
st.sidebar.title("📊 Ops Dashboard")
st.sidebar.caption("Marketing & Operations · AI-Augmented")

with st.sidebar.expander("🔑 Claude API key", expanded="ANTHROPIC_API_KEY" not in os.environ):
    key_input = st.text_input(
        "ANTHROPIC_API_KEY",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="Stored only for this session. Prefer a .env file for local dev.",
    )
    if key_input:
        os.environ["ANTHROPIC_API_KEY"] = key_input

df_all = du.load_data()
min_date, max_date = df_all["date"].min().date(), df_all["date"].max().date()
default_start = max(min_date, max_date - timedelta(days=13))

st.sidebar.subheader("Filters")
date_range = st.sidebar.date_input(
    "Date range",
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, max_date

all_channels = sorted(df_all["channel"].unique())
selected_channels = st.sidebar.multiselect("Channels", all_channels, default=all_channels)

st.sidebar.divider()
st.sidebar.caption(
    "Sample data is synthetic. Swap `data_utils.load_data()` to point at a "
    "real source (warehouse, API, spreadsheet)."
)

# ----------------------------------------------------------------------------
# Data prep
# ----------------------------------------------------------------------------
filtered = du.filter_data(df_all, start_date, end_date, selected_channels)
prev_start, prev_end = du.prior_period(start_date, end_date)
prior_filtered = du.filter_data(df_all, prev_start, prev_end, selected_channels)

daily = du.daily_rollup(filtered)
channel_agg = du.channel_summary(filtered)
kpis = du.compute_kpis(filtered, prior_filtered)
date_range_label = f"{start_date} to {end_date}"

# ----------------------------------------------------------------------------
# Header + KPI row
# ----------------------------------------------------------------------------
st.title("AI-Augmented Operations Dashboard")
st.caption(
    f"Showing **{date_range_label}** · {len(selected_channels)} channel(s) · "
    f"vs. prior period {prev_start.date()} to {prev_end.date()}"
)

kpi_cols = st.columns(len(kpis))
for col, (label, info) in zip(kpi_cols, kpis.items()):
    value = info["value"]
    display_value = f"{value:,.0f}" if abs(value) >= 100 else f"{value:,.2f}"
    if label == "Spend" or label == "Revenue":
        display_value = f"${value:,.0f}"
    delta = f"{info['delta_pct']:+.1f}%" if info["delta_pct"] is not None else None
    # Ticket backlog going up is bad, so invert the delta color for it.
    delta_color = "inverse" if label == "Avg Ticket Backlog" else "normal"
    col.metric(label, display_value, delta, delta_color=delta_color)

st.divider()

# ----------------------------------------------------------------------------
# Tabs: Charts | AI Briefing | Channel Insights | Anomalies | Full Report | Ask
# ----------------------------------------------------------------------------
tab_charts, tab_briefing, tab_channels, tab_anomalies, tab_report, tab_ask = st.tabs(
    ["📈 Charts", "🤖 Daily Briefing", "🎯 Channel Insights", "🚨 Anomaly Scan", "📄 Full Report", "💬 Ask the Data"]
)

with tab_charts:
    left, right = st.columns(2)
    with left:
        fig_rev = px.line(daily, x="date", y="revenue", markers=True, title="Daily Revenue")
        st.plotly_chart(fig_rev, use_container_width=True)

        fig_spend = px.bar(channel_agg, x="channel", y="spend", title="Spend by Channel", color="channel")
        st.plotly_chart(fig_spend, use_container_width=True)

    with right:
        fig_conv = px.line(daily, x="date", y="conv_rate_pct", markers=True, title="Daily Conversion Rate (%)")
        st.plotly_chart(fig_conv, use_container_width=True)

        fig_ops = px.line(
            daily, x="date", y=["support_ticket_backlog", "csat_score"],
            title="Support Backlog vs. CSAT", markers=True,
        )
        st.plotly_chart(fig_ops, use_container_width=True)

    st.subheader("Channel summary")
    st.dataframe(channel_agg, use_container_width=True, hide_index=True)

with tab_briefing:
    st.subheader("AI-generated daily briefing")
    st.caption("Claude reads the current KPI window and rollup, then writes the takeaways.")
    if st.button("Generate briefing", type="primary", key="briefing_btn"):
        with st.spinner("Asking Claude to review the numbers..."):
            try:
                briefing = ai_engine.generate_daily_briefing(daily, kpis, date_range_label)
                st.session_state["briefing"] = briefing
            except RuntimeError as e:
                st.error(str(e))
    if "briefing" in st.session_state:
        st.markdown(st.session_state["briefing"])

with tab_channels:
    st.subheader("AI-generated channel insights")
    st.caption("Claude compares ROAS, CAC, and conversion efficiency across channels.")
    if st.button("Generate channel insights", type="primary", key="channel_btn"):
        with st.spinner("Analyzing channel performance..."):
            try:
                insights = ai_engine.generate_channel_insights(channel_agg)
                st.session_state["channel_insights"] = insights
            except RuntimeError as e:
                st.error(str(e))
    if "channel_insights" in st.session_state:
        st.markdown(st.session_state["channel_insights"])

with tab_anomalies:
    st.subheader("AI anomaly scan")
    st.caption("Claude scans the daily time series for spikes, dips, and backlog build-ups.")
    if st.button("Scan for anomalies", type="primary", key="anomaly_btn"):
        with st.spinner("Scanning the time series..."):
            try:
                anomalies = ai_engine.generate_anomaly_scan(daily)
                st.session_state["anomalies"] = anomalies
            except RuntimeError as e:
                st.error(str(e))
    if "anomalies" in st.session_state:
        st.markdown(st.session_state["anomalies"])

with tab_report:
    st.subheader("Full stakeholder report draft")
    st.caption("A longer, structured write-up suitable for sharing as-is or lightly editing.")
    if st.button("Draft full report", type="primary", key="report_btn"):
        with st.spinner("Drafting the report..."):
            try:
                report = ai_engine.generate_full_report(daily, channel_agg, kpis, date_range_label)
                st.session_state["report"] = report
            except RuntimeError as e:
                st.error(str(e))
    if "report" in st.session_state:
        st.markdown(st.session_state["report"])
        st.download_button(
            "Download report as Markdown",
            st.session_state["report"],
            file_name=f"ops_report_{start_date}_{end_date}.md",
        )

with tab_ask:
    st.subheader("Ask a question about this data")
    question = st.text_input(
        "e.g. 'Which channel had the worst CAC trend this week?'",
        key="ask_input",
    )
    if st.button("Ask Claude", type="primary", key="ask_btn") and question:
        with st.spinner("Thinking..."):
            try:
                answer = ai_engine.ask_custom_question(question, daily, channel_agg)
                st.session_state["ask_answer"] = answer
            except RuntimeError as e:
                st.error(str(e))
    if "ask_answer" in st.session_state:
        st.markdown(st.session_state["ask_answer"])
