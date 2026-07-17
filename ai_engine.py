"""
ai_engine.py
Thin wrapper around the Anthropic Claude API that turns tabular ops/marketing
metrics into narrative insights, anomaly call-outs, and ready-to-send report
drafts.

All functions return plain strings (markdown) so they drop straight into
Streamlit via st.markdown().
"""

from __future__ import annotations

import os

import pandas as pd
from anthropic import Anthropic, APIError

# Pick the model via env var so it's easy to swap without touching code.
# claude-sonnet-5 is a good default: fast enough for an interactive dashboard,
# strong enough for reasoning over numeric summaries.
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You are an analytics copilot embedded in an internal \
marketing & operations dashboard. You are given pre-aggregated metrics \
(never raw event-level data) and must produce clear, decision-useful \
narrative for a busy marketing/ops manager.

Rules:
- Be concrete: cite the actual numbers you were given, don't invent figures.
- Prioritize. Lead with the single most important takeaway.
- Call out risks (budget waste, backlog build-up, CSAT drops) as well as wins.
- Suggest 1-3 specific, actionable next steps.
- Use short paragraphs and markdown bullet points. No long preamble.
- Keep the whole response under ~250 words unless asked for a full report.
"""


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your environment or a "
            ".env file before requesting AI insights."
        )
    return Anthropic(api_key=api_key)


def _call_claude(user_prompt: str, max_tokens: int = 800) -> str:
    client = _client()
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except APIError as e:
        return f"⚠️ Claude API error: {e}"

    text_parts = [block.text for block in message.content if block.type == "text"]
    return "\n".join(text_parts).strip()


def _df_to_compact_csv(df: pd.DataFrame, max_rows: int = 60) -> str:
    """Keep prompts small and cheap: truncate long frames and drop to CSV."""
    if len(df) > max_rows:
        df = df.tail(max_rows)
    return df.to_csv(index=False)


def generate_daily_briefing(daily_df: pd.DataFrame, kpis: dict, date_range: str) -> str:
    """A short, human-readable summary of how the business performed."""
    kpi_lines = []
    for label, info in kpis.items():
        delta = f"{info['delta_pct']:+.1f}%" if info["delta_pct"] is not None else "n/a"
        kpi_lines.append(f"- {label}: {info['value']:,.2f} (vs. prior period: {delta})")
    kpi_block = "\n".join(kpi_lines)

    prompt = f"""Period analyzed: {date_range}

Headline KPIs vs. the prior period of equal length:
{kpi_block}

Daily rollup (most recent rows, CSV):
{_df_to_compact_csv(daily_df)}

Write a daily operations briefing covering: what's working, what's at risk,
and 1-3 recommended actions for today."""
    return _call_claude(prompt)


def generate_channel_insights(channel_df: pd.DataFrame) -> str:
    """Compare channel performance and flag reallocation opportunities."""
    prompt = f"""Channel-level performance summary for the selected window (CSV):
{_df_to_compact_csv(channel_df)}

Columns: sessions, spend, conversions, revenue, csat_score, conv_rate_pct,
roas (revenue/spend), cac (spend/conversions).

Identify: the best and worst performing channels by ROAS, any channel where
spend looks misallocated relative to conversion efficiency, and a concrete
budget-shift recommendation."""
    return _call_claude(prompt)


def generate_anomaly_scan(daily_df: pd.DataFrame) -> str:
    """Look for spikes, dips, or backlog build-ups worth a human's attention."""
    prompt = f"""Daily operations time series (CSV):
{_df_to_compact_csv(daily_df, max_rows=90)}

Scan for anomalies: unusual spikes or drops in spend, conversions, revenue,
CAC, support ticket backlog, or CSAT. For each anomaly found, name the date,
the metric, and a plausible driver. If nothing stands out, say so plainly
instead of manufacturing a false positive."""
    return _call_claude(prompt)


def generate_full_report(daily_df: pd.DataFrame, channel_df: pd.DataFrame, kpis: dict, date_range: str) -> str:
    """A longer, shareable weekly/monthly report draft (e.g. for stakeholders)."""
    kpi_lines = []
    for label, info in kpis.items():
        delta = f"{info['delta_pct']:+.1f}%" if info["delta_pct"] is not None else "n/a"
        kpi_lines.append(f"- {label}: {info['value']:,.2f} (vs. prior period: {delta})")
    kpi_block = "\n".join(kpi_lines)

    prompt = f"""Draft a shareable stakeholder report for the period {date_range}.

Headline KPIs vs. prior period:
{kpi_block}

Channel summary (CSV):
{_df_to_compact_csv(channel_df)}

Daily rollup (CSV):
{_df_to_compact_csv(daily_df)}

Structure the report with markdown headers:
## Executive Summary
## Performance Highlights
## Risks & Watch Items
## Recommended Actions

This report may run longer than usual (it's a formal document, not a quick
briefing) but stay focused and avoid restating raw numbers that don't add
insight."""
    return _call_claude(prompt, max_tokens=1500)


def ask_custom_question(question: str, daily_df: pd.DataFrame, channel_df: pd.DataFrame) -> str:
    """Free-form Q&A grounded in the currently filtered dashboard data."""
    prompt = f"""A dashboard user is asking a free-form question about the data
currently on screen. Answer using only the data provided below; if the data
can't answer the question, say what's missing.

Question: {question}

Daily rollup (CSV):
{_df_to_compact_csv(daily_df)}

Channel summary (CSV):
{_df_to_compact_csv(channel_df)}"""
    return _call_claude(prompt)
