# extractors/world_bank_extractor.py
# Author: Gulian Ibrahim
# BRONZE LAYER — Extract SA economic indicators from the World Bank Open Data API.
# Completely free, no API key needed.

import json
import requests
import pandas as pd
from loguru import logger

from datetime import datetime, timezone

from config import WORLD_BANK_BASE_URL, WB_COUNTRY, WB_INDICATORS, BRONZE_DIR, DEFAULT_YEAR_RANGE


def fetch_indicator(indicator_code: str, year_from: int, year_to: int) -> list:
    """
    Fetch a single World Bank indicator for South Africa.
    Uses pagination to retrieve all available years.
    """
    url = f"{WORLD_BANK_BASE_URL}/country/{WB_COUNTRY}/indicator/{indicator_code}"
    params = {
        "format":    "json",
        "per_page":  100,
        "date":      f"{year_from}:{year_to}",
    }

    all_records = []
    page = 1

    while True:
        params["page"] = page
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"EXTRACT | World Bank fetch failed for {indicator_code}: {e}")
            raise

        if not data or len(data) < 2:
            break

        meta, records = data[0], data[1]
        all_records.extend(records or [])

        # World Bank API paginates — keep fetching until we have all pages
        if page >= meta.get("pages", 1):
            break
        page += 1

    return all_records


def extract_world_bank_indicators(
    year_from: int = DEFAULT_YEAR_RANGE[0],
    year_to:   int = DEFAULT_YEAR_RANGE[1],
) -> dict:
    """
    Pull all configured SA economic indicators from the World Bank.
    Saves raw JSON responses to the bronze layer.

    Returns a dict of indicator_name → list of raw records.
    """
    logger.info(f"EXTRACT | World Bank: pulling {len(WB_INDICATORS)} SA indicators ({year_from}–{year_to})")

    all_data = {}
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    for code, friendly_name in WB_INDICATORS.items():
        logger.info(f"EXTRACT |   → {friendly_name} ({code})")
        records = fetch_indicator(code, year_from, year_to)

        # Attach metadata
        payload = {
            "_ingested_at":   datetime.now(timezone.utc).isoformat(),
            "_indicator":     code,
            "_friendly_name": friendly_name,
            "_country":       WB_COUNTRY,
            "_source":        WORLD_BANK_BASE_URL,
            "records":        records,
        }

        # Save raw to bronze (one file per indicator)
        bronze_path = BRONZE_DIR / f"wb_{friendly_name}_{timestamp}.json"
        with open(bronze_path, "w") as f:
            json.dump(payload, f, indent=2)

        all_data[friendly_name] = {"payload": payload, "bronze_path": str(bronze_path)}
        logger.success(f"EXTRACT |   ✓ {len(records)} records saved → {bronze_path.name}")

    return all_data
