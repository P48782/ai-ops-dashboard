"""
data_utils.py
Data loading and aggregation helpers for the AI-Augmented Operations Dashboard.

Swap `load_data()` to pull from a real source (a warehouse query, a REST API,
Google Sheets, etc.) — everything downstream just expects a DataFrame with
these columns:

    date, channel, sessions, spend, conversions, revenue,
    conv_rate_pct, support_ticket_backlog, csat_score
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

DATA_PATH = "ops_marketing_data.csv"


@st.cache_data(show_spinner=False)
def load_data(path: str = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def filter_data(
    df: pd.DataFrame,
    start_date,
    end_date,
    channels: list[str] | None = None,
) -> pd.DataFrame:
    mask = (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))
    filtered = df.loc[mask]
    if channels:
        filtered = filtered[filtered["channel"].isin(channels)]
    return filtered


def daily_rollup(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the (date, channel) grain up to a single row per day."""
    agg = (
        df.groupby("date", as_index=False)
        .agg(
            sessions=("sessions", "sum"),
            spend=("spend", "sum"),
            conversions=("conversions", "sum"),
            revenue=("revenue", "sum"),
            support_ticket_backlog=("support_ticket_backlog", "sum"),
            csat_score=("csat_score", "mean"),
        )
    )
    agg["conv_rate_pct"] = (agg["conversions"] / agg["sessions"] * 100).round(2)
    agg["cac"] = (agg["spend"] / agg["conversions"].replace(0, np.nan)).round(2)
    return agg


def channel_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to a single row per channel for the selected window."""
    agg = (
        df.groupby("channel", as_index=False)
        .agg(
            sessions=("sessions", "sum"),
            spend=("spend", "sum"),
            conversions=("conversions", "sum"),
            revenue=("revenue", "sum"),
            csat_score=("csat_score", "mean"),
        )
    )
    agg["conv_rate_pct"] = (agg["conversions"] / agg["sessions"] * 100).round(2)
    agg["roas"] = (agg["revenue"] / agg["spend"].replace(0, np.nan)).round(2)
    agg["cac"] = (agg["spend"] / agg["conversions"].replace(0, np.nan)).round(2)
    return agg.sort_values("revenue", ascending=False)


def compute_kpis(df: pd.DataFrame, prior_df: pd.DataFrame) -> dict:
    """Current-window KPIs plus % change vs. the prior window of equal length."""

    def _sum(frame, col):
        return float(frame[col].sum()) if len(frame) else 0.0

    def _pct_change(cur, prev):
        if prev == 0:
            return None
        return round((cur - prev) / prev * 100, 1)

    kpis = {}
    for label, col in [
        ("Sessions", "sessions"),
        ("Spend", "spend"),
        ("Conversions", "conversions"),
        ("Revenue", "revenue"),
    ]:
        cur = _sum(df, col)
        prev = _sum(prior_df, col)
        kpis[label] = {"value": cur, "delta_pct": _pct_change(cur, prev)}

    cur_backlog = df["support_ticket_backlog"].mean() if len(df) else 0
    prev_backlog = prior_df["support_ticket_backlog"].mean() if len(prior_df) else 0
    kpis["Avg Ticket Backlog"] = {
        "value": round(cur_backlog, 1),
        "delta_pct": _pct_change(cur_backlog, prev_backlog),
    }

    cur_csat = df["csat_score"].mean() if len(df) else 0
    prev_csat = prior_df["csat_score"].mean() if len(prior_df) else 0
    kpis["Avg CSAT"] = {
        "value": round(cur_csat, 1),
        "delta_pct": _pct_change(cur_csat, prev_csat),
    }

    return kpis


def prior_period(start_date, end_date):
    """Return the (start, end) of the period immediately preceding the given window."""
    span = (pd.Timestamp(end_date) - pd.Timestamp(start_date))
    prev_end = pd.Timestamp(start_date) - pd.Timedelta(days=1)
    prev_start = prev_end - span
    return prev_start, prev_end
