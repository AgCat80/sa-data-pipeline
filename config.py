# config.py
# Author: Gulian Ibrahim
# Central configuration for the SA Data Pipeline.

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
BRONZE_DIR  = DATA_DIR / "bronze"
SILVER_DIR  = DATA_DIR / "silver"
GOLD_DIR    = DATA_DIR / "gold"
DB_PATH     = DATA_DIR / "sa_pipeline.duckdb"

# Ensure directories exist
for d in [BRONZE_DIR, SILVER_DIR, GOLD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── API endpoints (all free, no key required) ────────────────────────────────
EXCHANGE_RATE_URL   = "https://open.er-api.com/v6/latest/USD"
WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2"

# World Bank indicators for South Africa
WB_COUNTRY   = "ZA"
WB_INDICATORS = {
    "NY.GDP.MKTP.CD":    "gdp_usd",            # GDP current USD
    "NY.GDP.PCAP.CD":    "gdp_per_capita_usd", # GDP per capita
    "FP.CPI.TOTL.ZG":    "inflation_rate",      # Inflation (CPI %)
    "SL.UEM.TOTL.ZS":    "unemployment_rate",   # Unemployment %
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_rate",     # GDP growth %
    "SP.POP.TOTL":        "population",          # Total population
}

# ── Pipeline settings ────────────────────────────────────────────────────────
PIPELINE_NAME       = "sa-economic-data-pipeline"
PIPELINE_VERSION    = "1.0.0"
DEFAULT_YEAR_RANGE  = (2010, 2024)
