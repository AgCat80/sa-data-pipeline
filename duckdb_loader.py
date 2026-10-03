# loaders/duckdb_loader.py
# Author: Gulian Ibrahim
# LOAD STEP — Load transformed data into DuckDB, the analytical data warehouse.
# DuckDB is a columnar, embedded analytical database (think SQLite for data engineering).
# Each gold-layer table gets its own schema in the warehouse.

import duckdb
import pandas as pd
from datetime import datetime
from loguru import logger

from config import DB_PATH


class DuckDBLoader:
    """
    Manages all writes to the local DuckDB analytical warehouse.
    Uses context manager pattern to ensure connections are always closed cleanly.
    """

    def __init__(self):
        self.db_path = str(DB_PATH)

    def __enter__(self):
        self.conn = duckdb.connect(self.db_path)
        self._init_schema()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def _init_schema(self):
        """Create warehouse tables if they don't already exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS economic_summary (
                year                    INTEGER,
                country                 VARCHAR,
                gdp_usd                 DOUBLE,
                gdp_per_capita_usd      DOUBLE,
                gdp_growth_rate         DOUBLE,
                inflation_rate          DOUBLE,
                unemployment_rate       DOUBLE,
                population              DOUBLE,
                economic_health_score   DOUBLE,
                decade                  VARCHAR,
                gdp_usd_yoy_change      DOUBLE,
                gdp_growth_rate_yoy_change  DOUBLE,
                inflation_rate_yoy_change   DOUBLE,
                unemployment_rate_yoy_change DOUBLE,
                gold_built_at           VARCHAR,
                loaded_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fx_snapshot (
                base_currency       VARCHAR,
                quote_currency      VARCHAR,
                rate                DOUBLE,
                zar_equivalent      DOUBLE,
                zar_to_currency     DOUBLE,
                update_ts           TIMESTAMP,
                ingested_at         VARCHAR,
                gold_built_at       VARCHAR,
                loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id          VARCHAR,
                run_started_at  TIMESTAMP,
                run_finished_at TIMESTAMP,
                status          VARCHAR,
                records_loaded  INTEGER,
                notes           VARCHAR
            )
        """)
        logger.info("LOAD | DuckDB schema initialised")

    def load_economic_summary(self, df: pd.DataFrame) -> int:
        """
        Upsert the economic summary gold table.
        Replaces rows for years already in the table, inserts new ones.
        """
        if df.empty:
            logger.warning("LOAD | Economic summary DataFrame is empty, skipping")
            return 0

        # Remove existing rows for the same years to avoid duplicates
        years = df["year"].tolist()
        placeholders = ", ".join(["?" for _ in years])
        self.conn.execute(
            f"DELETE FROM economic_summary WHERE year IN ({placeholders})", years
        )

        # Insert new rows
        self.conn.execute(
            "CREATE OR REPLACE TABLE economic_summary AS SELECT * FROM df",
        )

        count = len(df)
        logger.success(f"LOAD | economic_summary: {count} rows loaded into DuckDB")
        return count

    def load_fx_snapshot(self, df: pd.DataFrame) -> int:
        """
        Append the latest FX snapshot. FX data is timestamped so we keep history.
        """
        if df.empty:
            logger.warning("LOAD | FX snapshot DataFrame is empty, skipping")
            return 0

        # Keep only the columns that exist in both the table and the df
        expected_cols = [
            "base_currency", "quote_currency", "rate", "zar_equivalent",
            "zar_to_currency", "update_ts", "ingested_at", "gold_built_at"
        ]
        df_clean = df[[c for c in expected_cols if c in df.columns]].copy()

        self.conn.execute("CREATE OR REPLACE TABLE fx_snapshot AS SELECT * FROM df_clean")

        count = len(df_clean)
        logger.success(f"LOAD | fx_snapshot: {count} rows loaded into DuckDB")
        return count

    def log_pipeline_run(self, run_id: str, started: datetime,
                          finished: datetime, status: str,
                          records: int, notes: str = ""):
        """Record metadata about this pipeline run for auditing."""
        self.conn.execute("""
            INSERT INTO pipeline_runs
            (run_id, run_started_at, run_finished_at, status, records_loaded, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [run_id, started, finished, status, records, notes])
        logger.info(f"LOAD | Pipeline run logged: {run_id} — {status}")

    def query(self, sql: str) -> pd.DataFrame:
        """Run any SQL query and return a Pandas DataFrame. Useful for dashboard."""
        return self.conn.execute(sql).df()
