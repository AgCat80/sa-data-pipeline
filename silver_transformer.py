# transformers/silver_transformer.py
# Author: Gulian Ibrahim
# SILVER LAYER — Clean, validate, and normalise raw bronze data.
# This is the TRANSFORM step in the ETL pipeline.
# Bronze = raw API data. Silver = clean, typed, validated data.

import pandas as pd
from datetime import datetime, timezone
from loguru import logger

from config import SILVER_DIR


def transform_exchange_rates(raw_data: dict) -> pd.DataFrame:
    """
    Transform raw exchange rate JSON into a clean, typed DataFrame.
    Extracts ZAR-related pairs and derives useful computed columns.
    """
    logger.info("TRANSFORM | Cleaning exchange rate data → silver layer")

    rates     = raw_data["raw"].get("rates", {})
    base      = raw_data["raw"].get("base_code", "USD")
    update_ts = raw_data["raw"].get("time_last_update_utc", "")

    # Build one row per currency pair involving ZAR
    records = []
    zar_rate = rates.get("ZAR")

    if not zar_rate:
        logger.warning("TRANSFORM | ZAR rate not found in response")
        return pd.DataFrame()

    for currency, rate in rates.items():
        if rate and currency != base:
            records.append({
                "base_currency":   base,
                "quote_currency":  currency,
                "rate":            rate,
                # How many ZAR does this currency buy?
                "zar_equivalent":  zar_rate / rate if rate else None,
                "update_ts":       update_ts,
                "ingested_at":     datetime.now(timezone.utc).isoformat(),
            })

    df = pd.DataFrame(records)

    # Data quality checks
    df = df.dropna(subset=["rate", "zar_equivalent"])
    df = df[df["rate"] > 0]
    df["rate"]          = df["rate"].round(6)
    df["zar_equivalent"] = df["zar_equivalent"].round(4)
    df["update_ts"]     = pd.to_datetime(df["update_ts"], utc=True, errors="coerce")

    # Save to silver layer as parquet (efficient columnar format)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    silver_path  = SILVER_DIR / f"exchange_rates_{timestamp}.parquet"
    df.to_parquet(silver_path, index=False)

    logger.success(f"TRANSFORM | Exchange rates → silver: {len(df)} rows, saved to {silver_path.name}")
    return df


def transform_world_bank(wb_raw: dict) -> pd.DataFrame:
    """
    Transform raw World Bank indicator records into a clean wide-format DataFrame.
    One row per year, one column per indicator.
    Removes null values, casts numeric types, derives year-over-year change columns.
    """
    logger.info("TRANSFORM | Cleaning World Bank data → silver layer")

    frames = []

    for indicator_name, content in wb_raw.items():
        records = content["payload"].get("records", [])
        if not records:
            logger.warning(f"TRANSFORM | No records for {indicator_name}")
            continue

        rows = []
        for rec in records:
            # World Bank returns nulls for years without data — we drop them
            if rec.get("value") is None:
                continue
            rows.append({
                "year":      int(rec["date"]),
                "country":   rec.get("country", {}).get("value", "South Africa"),
                "indicator": indicator_name,
                "value":     float(rec["value"]),
            })

        if rows:
            frames.append(pd.DataFrame(rows))

    if not frames:
        logger.warning("TRANSFORM | No World Bank data to transform")
        return pd.DataFrame()

    # Stack all indicators into a long-format DataFrame
    long_df = pd.concat(frames, ignore_index=True)

    # Pivot to wide format: one row per year, one column per indicator
    wide_df = long_df.pivot_table(
        index=["year", "country"],
        columns="indicator",
        values="value",
        aggfunc="first",
    ).reset_index()
    wide_df.columns.name = None

    # Sort by year ascending
    wide_df = wide_df.sort_values("year").reset_index(drop=True)

    # Derive year-over-year change for key indicators
    for col in ["gdp_usd", "gdp_growth_rate", "inflation_rate", "unemployment_rate"]:
        if col in wide_df.columns:
            wide_df[f"{col}_yoy_change"] = wide_df[col].diff().round(4)

    wide_df["ingested_at"] = datetime.now(timezone.utc).isoformat()

    # Save to silver as parquet
    timestamp   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    silver_path = SILVER_DIR / f"world_bank_sa_{timestamp}.parquet"
    wide_df.to_parquet(silver_path, index=False)

    logger.success(f"TRANSFORM | World Bank SA data → silver: {len(wide_df)} rows ({wide_df['year'].min()}–{wide_df['year'].max()})")
    return wide_df
