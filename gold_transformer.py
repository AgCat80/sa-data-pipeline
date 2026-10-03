# transformers/gold_transformer.py
# Author: Gulian Ibrahim
# GOLD LAYER — Produce analytics-ready, aggregated datasets from silver data.
# Gold = curated, business-level tables ready for dashboards and reporting.
# This is the final transformation step in the medallion architecture.

import pandas as pd
from datetime import datetime, timezone
from loguru import logger

from config import GOLD_DIR


def build_gold_economic_summary(wb_silver_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a gold-layer economic summary table for South Africa.
    Adds rolling averages, decade groupings, and normalised scores.
    This is what gets displayed on the dashboard.
    """
    logger.info("TRANSFORM | Building gold economic summary")

    if wb_silver_df.empty:
        logger.warning("TRANSFORM | Silver DataFrame is empty, skipping gold build")
        return pd.DataFrame()

    df = wb_silver_df.copy()

    # ── Rolling averages (3-year window for smoothing) ──────────────────────
    numeric_cols = [c for c in df.columns if df[c].dtype in ["float64", "int64"]
                    and c not in ["year"]]
    for col in numeric_cols:
        df[f"{col}_3yr_avg"] = df[col].rolling(window=3, min_periods=1).mean().round(4)

    # ── Decade grouping ──────────────────────────────────────────────────────
    df["decade"] = (df["year"] // 10 * 10).astype(str) + "s"

    # ── Economic health score (composite index 0–100) ────────────────────────
    # Simple weighted composite: lower unemployment is better, higher GDP growth is better
    # This is a simplified scoring model for portfolio demonstration
    if all(c in df.columns for c in ["gdp_growth_rate", "inflation_rate", "unemployment_rate"]):
        df["gdp_growth_norm"]      = (df["gdp_growth_rate"]    / df["gdp_growth_rate"].max()).clip(0, 1)
        df["inflation_penalty"]    = (df["inflation_rate"]     / df["inflation_rate"].max()).clip(0, 1)
        df["unemployment_penalty"] = (df["unemployment_rate"]  / df["unemployment_rate"].max()).clip(0, 1)

        df["economic_health_score"] = (
            (df["gdp_growth_norm"]      * 0.5)  -
            (df["inflation_penalty"]    * 0.25) -
            (df["unemployment_penalty"] * 0.25)
        ) * 100
        df["economic_health_score"] = df["economic_health_score"].round(2)

        # Drop intermediate columns
        df = df.drop(columns=["gdp_growth_norm", "inflation_penalty", "unemployment_penalty"])

    df["gold_built_at"] = datetime.now(timezone.utc).isoformat()

    # Save to gold
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    gold_path = GOLD_DIR / f"sa_economic_summary_{timestamp}.parquet"
    df.to_parquet(gold_path, index=False)

    logger.success(f"TRANSFORM | Gold economic summary built: {len(df)} rows → {gold_path.name}")
    return df


def build_gold_exchange_snapshot(fx_silver_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a gold-layer ZAR exchange rate snapshot.
    Filters to major world currencies against ZAR, adds a rating label.
    """
    logger.info("TRANSFORM | Building gold exchange rate snapshot")

    if fx_silver_df.empty:
        return pd.DataFrame()

    major_currencies = ["EUR", "GBP", "JPY", "CNY", "AUD", "CAD", "CHF", "INR", "BRL", "NGN"]

    df = fx_silver_df[
        (fx_silver_df["base_currency"] == "USD") &
        (fx_silver_df["quote_currency"].isin(major_currencies))
    ].copy()

    # Add a strength label for ZAR relative to each currency
    zar_rate = fx_silver_df.loc[fx_silver_df["quote_currency"] == "ZAR", "rate"].values
    if len(zar_rate):
        zar_rate = zar_rate[0]
        df["zar_to_currency"] = (zar_rate / df["rate"]).round(4)

    df["gold_built_at"] = datetime.now(timezone.utc).isoformat()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    gold_path = GOLD_DIR / f"sa_fx_snapshot_{timestamp}.parquet"
    df.to_parquet(gold_path, index=False)

    logger.success(f"TRANSFORM | Gold FX snapshot built: {len(df)} rows → {gold_path.name}")
    return df
