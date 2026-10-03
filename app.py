# dashboard/app.py
# Author: Gulian Ibrahim
# Streamlit dashboard — reads from the DuckDB warehouse and displays
# SA economic data in an interactive, clean UI.
#
# Run: streamlit run dashboard/app.py

import sys
from pathlib import Path

# Allow imports from project root when running from dashboard/
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from loguru import logger

from loaders.duckdb_loader import DuckDBLoader
from config import DB_PATH
from datetime import datetime, timezone

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title  = "SA Economic Data Pipeline",
    page_icon   = "🇿🇦",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #0B1622; border-right: 1px solid #1A3348; }
  [data-testid="metric-container"] {
    background: #0B1622;
    border: 1px solid #1A3348;
    border-radius: 0;
    padding: 1rem;
  }
  [data-testid="metric-container"] label { color: #5A7A90; font-family: monospace; font-size: 0.75rem; letter-spacing: 0.1em; }
  [data-testid="metric-container"] [data-testid="metric-value"] { color: #00FFD1; font-family: monospace; }
  div.stTabs [data-baseweb="tab"] { font-family: monospace; color: #5A7A90; }
  div.stTabs [aria-selected="true"] { color: #00FFD1; border-bottom: 2px solid #00FFD1; }
  .stButton > button { font-family: monospace; background: transparent; border: 1px solid #00FFD1; color: #00FFD1; border-radius: 0; }
  .stButton > button:hover { background: #00FFD1; color: #040D14; }
  h1, h2, h3 { font-family: monospace !important; color: #fff !important; }
</style>
""", unsafe_allow_html=True)

def metric_card(label, value, delta=None):
    delta_html = f"<div style='color:#00FFD1;font-size:.8rem'>{delta}</div>" if delta else ""
    st.markdown(f"""
    <div style='background:#0B1622;border:1px solid #1A3348;padding:1rem 1.25rem;margin-bottom:.5rem'>
      <div style='font-family:monospace;font-size:.7rem;color:#5A7A90;letter-spacing:.1em'>{label}</div>
      <div style='font-family:monospace;font-size:1.6rem;color:#fff;font-weight:700'>{value}</div>
      {delta_html}
    </div>
    """, unsafe_allow_html=True)

# ── Custom styling ───────────────────────────────────────────────────────────
st.markdown("""
<style>
  .block-container { padding-top: 2rem; }
  .metric-card {
    background: #0e1117; border: 1px solid #333;
    border-radius: 8px; padding: 1rem;
  }
  h1, h2, h3 { font-family: monospace; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # Cache data for 5 minutes
def load_data():
    """Load all tables from DuckDB."""
    if not DB_PATH.exists():
        return None, None, None

    with DuckDBLoader() as db:
        econ = db.query("SELECT * FROM economic_summary ORDER BY year")
        fx   = db.query("""
            SELECT * FROM fx_snapshot
            WHERE ingested_at = (SELECT MAX(ingested_at) FROM fx_snapshot)
            ORDER BY zar_equivalent DESC
        """)
        runs = db.query("SELECT * FROM pipeline_runs ORDER BY run_started_at DESC LIMIT 10")

    return econ, fx, runs


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🇿🇦 SA Data Pipeline")
    st.caption("Built by **Gulian (Isaac) Ibrahim**")
    st.divider()

    st.markdown(f"`{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`")

    if st.button("▶ Run Pipeline Now", use_container_width=True, type="primary"):
        with st.spinner("Running full ETL pipeline..."):
            try:
                import subprocess
                import sys
                result = subprocess.run(
                    [sys.executable, "pipeline.py"],
                    capture_output=True, text=True, cwd=str(Path(__file__).parent.parent)
                )
                if result.returncode == 0:
                    st.success("Pipeline completed successfully!")
                    st.cache_data.clear()
                else:
                    st.error(f"Pipeline failed: {result.stderr[:300]}")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.caption("**Stack**")
    st.code("Python • DuckDB\nPandas • Streamlit\nWorld Bank API\nOpen Exchange Rates")
    st.caption("**Architecture**")
    st.code("Bronze → Silver → Gold\n(Medallion Architecture)")


# ── Main content ──────────────────────────────────────────────────────────────
st.title("SA Economic Data Pipeline")
st.caption("Live data from World Bank Open Data and Open Exchange Rates. Updated every 6 hours.")

econ_df, fx_df, runs_df = load_data()

if econ_df is None or econ_df.empty:
    st.warning("No data in warehouse yet. Click **Run Pipeline Now** in the sidebar to load data.")
    st.stop()

# ── KPI metrics ──────────────────────────────────────────────────────────────
latest = econ_df.iloc[-1]
prev   = econ_df.iloc[-2] if len(econ_df) > 1 else latest

col1, col2, col3, col4 = st.columns(4)

with col1:
    gdp_b = latest.get("gdp_usd", 0) / 1e9 if pd.notna(latest.get("gdp_usd")) else 0
    prev_b = prev.get("gdp_usd", 0) / 1e9 if pd.notna(prev.get("gdp_usd")) else 0
    metric_card("GDP (USD)", f"${gdp_b:,.0f}B", delta=f"{gdp_b - prev_b:+.0f}B")

with col2:
    gr = latest.get("gdp_growth_rate")
    metric_card("GDP Growth", f"{gr:.2f}%" if pd.notna(gr) else "N/A")

with col3:
    infl = latest.get("inflation_rate")
    metric_card("Inflation", f"{infl:.2f}%" if pd.notna(infl) else "N/A")

with col4:
    unemp = latest.get("unemployment_rate")
    metric_card("Unemployment", f"{unemp:.1f}%" if pd.notna(unemp) else "N/A")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 Economic Trends", "💱 Exchange Rates", "🏥 Health Score", "🔧 Pipeline Runs"])

with tab1:
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("GDP Growth Rate (%)")
        if "gdp_growth_rate" in econ_df.columns:
            fig = px.bar(
                econ_df.dropna(subset=["gdp_growth_rate"]),
                x="year", y="gdp_growth_rate",
                color="gdp_growth_rate",
                color_continuous_scale="RdYlGn",
                labels={"gdp_growth_rate": "Growth %", "year": "Year"},
            )
            fig.update_layout(showlegend=False,
                              coloraxis_showscale=False,
                              paper_bgcolor='#040D14',
                              plot_bgcolor='#0B1622',
                              font=dict(family='monospace', color='#C8D8E8'),
                              xaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                              yaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                              margin=dict(l=20, r=20, t=40, b=20),
                            )
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Inflation vs Unemployment (%)")
        if all(c in econ_df.columns for c in ["inflation_rate", "unemployment_rate"]):
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=econ_df["year"], y=econ_df["inflation_rate"],
                name="Inflation", line=dict(color="#FF4B4B")
            ))
            fig.add_trace(go.Scatter(
                x=econ_df["year"], y=econ_df["unemployment_rate"],
                name="Unemployment", line=dict(color="#0083B8")
            ))
            fig.update_layout(legend=dict(orientation="h"),
                              paper_bgcolor='#040D14',
                              plot_bgcolor='#0B1622',
                              font=dict(family='monospace', color='#C8D8E8'),
                              xaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                              yaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                              margin=dict(l=20, r=20, t=40, b=20),
                            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("GDP (USD billions) Over Time")
    if "gdp_usd" in econ_df.columns:
        plot_df = econ_df.dropna(subset=["gdp_usd"]).copy()
        plot_df["gdp_b"] = plot_df["gdp_usd"] / 1e9
        fig = px.area(plot_df, x="year", y="gdp_b", labels={"gdp_b": "GDP (USD Billions)"})
        fig.update_traces(line_color="#00D26A", fillcolor="rgba(0, 210, 106, 0.15)")
        fig.update_layout(paper_bgcolor='#040D14',
                          plot_bgcolor='#0B1622',
                          font=dict(family='monospace', color='#C8D8E8'),
                          xaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                          yaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                          margin=dict(l=20, r=20, t=40, b=20),
                       )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Current ZAR Exchange Rates")
    if fx_df is not None and not fx_df.empty:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            fig = px.bar(
                fx_df.head(12),
                x="quote_currency", y="zar_equivalent",
                labels={"zar_equivalent": "ZAR equivalent of 1 USD", "quote_currency": "Currency"},
                color="zar_equivalent", color_continuous_scale="Blues",
            )
            fig.update_layout(coloraxis_showscale=False,
                              paper_bgcolor='#040D14',
                              plot_bgcolor='#0B1622',
                              font=dict(family='monospace', color='#C8D8E8'),
                              xaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                              yaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                              margin=dict(l=20, r=20, t=40, b=20),
                          )
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.dataframe(
                fx_df[["quote_currency", "rate", "zar_equivalent"]].head(12),
                hide_index=True, use_container_width=True
            )
    else:
        st.info("Exchange rate data not yet loaded.")

with tab3:
    st.subheader("SA Economic Health Score (Composite Index)")
    if "economic_health_score" in econ_df.columns:
        fig = px.line(
            econ_df.dropna(subset=["economic_health_score"]),
            x="year", y="economic_health_score",
            markers=True,
            labels={"economic_health_score": "Health Score"},
        )
        fig.update_traces(line_color="#8B5CF6", marker_color="#00FFD1")
        fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Neutral")
        fig.update_layout(paper_bgcolor='#040D14',
                          plot_bgcolor='#0B1622',
                          font=dict(family='monospace', color='#C8D8E8'),
                          xaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                          yaxis=dict(gridcolor='#1A3348', zerolinecolor='#1A3348'),
                          margin=dict(l=20, r=20, t=40, b=20),
                       )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Composite score based on GDP growth, inflation and unemployment. Positive = healthier economy.")
    else:
        st.info("Economic health score not yet computed. Run the pipeline.")

with tab4:
    st.subheader("Pipeline Run History")
    if runs_df is not None and not runs_df.empty:
        st.dataframe(runs_df, hide_index=True, use_container_width=True)
    else:
        st.info("No pipeline runs logged yet.")
