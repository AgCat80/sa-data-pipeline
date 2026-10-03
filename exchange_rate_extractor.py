# extractors/exchange_rate_extractor.py
# Author: Gulian Ibrahim
# BRONZE LAYER — Extract raw exchange rate data from the Open Exchange Rates API.
# No API key required. Saves raw JSON to the bronze data directory.

import json
import requests
from datetime import datetime
from pathlib import Path
from loguru import logger

from config import EXCHANGE_RATE_URL, BRONZE_DIR
from datetime import datetime, timezone


def extract_exchange_rates() -> dict:
    """
    Fetch current exchange rates with USD as the base currency.
    Returns the raw response dict and saves it to bronze storage.

    This is the EXTRACT step in the ETL pipeline.
    """
    logger.info("EXTRACT | Fetching exchange rates from open.er-api.com")

    try:
        response = requests.get(EXCHANGE_RATE_URL, timeout=15)
        response.raise_for_status()
        raw_data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"EXTRACT | Exchange rate fetch failed: {e}")
        raise

    # Stamp ingestion metadata before saving to bronze
    raw_data["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    raw_data["_source"]      = EXCHANGE_RATE_URL
    raw_data["_pipeline"]    = "sa-economic-data-pipeline"

    # Save raw to bronze layer (exact copy of what the API returned)
    timestamp  = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bronze_path = BRONZE_DIR / f"exchange_rates_{timestamp}.json"
    with open(bronze_path, "w") as f:
        json.dump(raw_data, f, indent=2)

    logger.success(f"EXTRACT | Exchange rates saved to bronze: {bronze_path.name}")

    # Pull out the currencies we care about for SA analysis
    rates = raw_data.get("rates", {})
    key_pairs = {
        "USD_ZAR": rates.get("ZAR"),
        "EUR_ZAR": rates.get("ZAR") / rates.get("EUR", 1) if rates.get("EUR") else None,
        "GBP_ZAR": rates.get("ZAR") / rates.get("GBP", 1) if rates.get("GBP") else None,
        "USD_ZAR_INVERTED": 1 / rates["ZAR"] if rates.get("ZAR") else None,
    }

    logger.info(f"EXTRACT | USD/ZAR: {key_pairs['USD_ZAR']:.4f}")
    return {"raw": raw_data, "key_pairs": key_pairs, "bronze_path": str(bronze_path)}
