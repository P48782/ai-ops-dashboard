# AI-Augmented Operations Dashboard

A live Streamlit dashboard for marketing & operations metrics that uses the
Anthropic Claude API to turn raw KPIs into narrative insights: daily
briefings, channel-performance analysis, anomaly detection, and shareable
report drafts — generated on demand from whatever data is currently on
screen.

**Stack:** Python · Streamlit · Pandas · Plotly · Anthropic Claude API

## Features

- **Live KPI dashboard** — sessions, spend, conversions, revenue, support
  backlog, and CSAT, with period-over-period deltas and channel breakdowns.
- **AI daily briefing** — Claude summarizes what's working, what's at risk,
  and what to do about it.
- **Channel insights** — Claude compares ROAS/CAC/conversion efficiency
  across channels and flags reallocation opportunities.
- **Anomaly scan** — Claude reviews the daily time series for spikes, dips,
  and backlog build-ups worth a human's attention.
- **Full report drafting** — a structured, stakeholder-ready report
  (Executive Summary / Highlights / Risks / Recommended Actions),
  downloadable as Markdown.
- **Ask the data** — free-form Q&A grounded in the currently filtered data.

## Project structure

```
ai_ops_dashboard/
├── app.py                       # Streamlit app (UI, filters, tabs)
├── ai_engine.py                 # Claude API calls + prompt templates
├── data_utils.py                # Data loading, filtering, aggregation
├── sample_data/
│   └── ops_marketing_data.csv   # Synthetic sample dataset (90 days × 5 channels)
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. **Install dependencies** (Python 3.10+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. **Set your Anthropic API key.** Either:

   - Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY`, or
   - Paste the key into the "🔑 Claude API key" box in the app sidebar at
     runtime (session-only, not persisted).

   Get a key from the [Anthropic Console](https://console.anthropic.com).

3. **Run it:**

   ```bash
   streamlit run app.py
   ```

   The app opens at `http://localhost:8501`.

## Using your own data

Swap out `sample_data/ops_marketing_data.csv` or point `data_utils.load_data()`
at a different source (a warehouse query, an internal API, a Google Sheet).
Everything downstream expects a DataFrame with these columns:

| column                    | meaning                              |
|----------------------------|---------------------------------------|
| `date`                    | ISO date, one row per (date, channel) |
| `channel`                 | marketing/traffic channel name        |
| `sessions`                | site/app sessions                     |
| `spend`                   | marketing spend for that channel/day  |
| `conversions`             | conversions attributed to the channel |
| `revenue`                 | revenue attributed to the channel     |
| `conv_rate_pct`           | conversions / sessions × 100          |
| `support_ticket_backlog`  | open support tickets that day         |
| `csat_score`              | customer satisfaction score (0–100)   |

If your schema differs, adjust the `groupby`/aggregation logic in
`data_utils.py` accordingly — the AI prompts in `ai_engine.py` just consume
whatever columns are in the DataFrames they're given, so they don't need
changes unless you rename columns.

## Notes on the AI layer

- Prompts in `ai_engine.py` only ever see **pre-aggregated** metrics (daily
  rollups and channel summaries), not raw event-level or PII data — keep it
  that way if you connect a real backend.
- The model is configurable via the `ANTHROPIC_MODEL` env var
  (defaults to `claude-sonnet-5`). Use a smaller/faster model if you want
  cheaper, snappier interactive responses, or a larger one for the full
  report draft.
- Each AI action is a separate, on-demand API call (not run automatically on
  every filter change) to keep token usage predictable.

## Extending this further

- Swap the CSV for a live connector (warehouse, CRM, ad platforms) in
  `data_utils.load_data()`.
- Add scheduled runs (e.g. via `cron` + a headless script that calls
  `ai_engine.generate_full_report()` and emails/Slacks the output) for
  automated recurring reporting.
- Add authentication (e.g. `streamlit-authenticator`) before deploying
  anywhere outside a trusted internal network.
