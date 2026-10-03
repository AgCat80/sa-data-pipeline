# pipeline.py
# Author: Gulian Ibrahim
# Main pipeline orchestrator. Runs the full ETL sequence:
#   Extract (bronze) → Transform (silver → gold) → Load (DuckDB warehouse)
#
# Run manually:   python pipeline.py
# Schedule:       python pipeline.py --schedule   (runs every 6 hours)

import uuid
import argparse
import schedule
import time
from datetime import datetime, timezone
from loguru import logger

from extractors.exchange_rate_extractor import extract_exchange_rates
from extractors.world_bank_extractor    import extract_world_bank_indicators
from transformers.silver_transformer   import transform_exchange_rates, transform_world_bank
from transformers.gold_transformer     import build_gold_economic_summary, build_gold_exchange_snapshot
from loaders.duckdb_loader             import DuckDBLoader
from config                            import PIPELINE_NAME, PIPELINE_VERSION


def run_pipeline() -> dict:
    """
    Execute one full pipeline run: Extract → Transform → Load.
    Returns a summary dict with status and record counts.
    """
    run_id     = str(uuid.uuid4())[:8]
    started_at = datetime.now(timezone.utc)
    total_records = 0

    logger.info(f"{'='*60}")
    logger.info(f"PIPELINE | {PIPELINE_NAME} v{PIPELINE_VERSION}")
    logger.info(f"PIPELINE | Run ID: {run_id} | Started: {started_at.isoformat()}")
    logger.info(f"{'='*60}")

    status = "SUCCESS"
    notes  = []

    try:
        # ── EXTRACT (Bronze Layer) ────────────────────────────────────────────
        logger.info("PIPELINE | Step 1/3 — EXTRACT")

        fx_raw = extract_exchange_rates()
        wb_raw = extract_world_bank_indicators()

        # ── TRANSFORM (Silver → Gold) ─────────────────────────────────────────
        logger.info("PIPELINE | Step 2/3 — TRANSFORM")

        fx_silver  = transform_exchange_rates(fx_raw)
        wb_silver  = transform_world_bank(wb_raw)
        econ_gold  = build_gold_economic_summary(wb_silver)
        fx_gold    = build_gold_exchange_snapshot(fx_silver)

        # ── LOAD (DuckDB Warehouse) ───────────────────────────────────────────
        logger.info("PIPELINE | Step 3/3 — LOAD")

        with DuckDBLoader() as loader:
            total_records += loader.load_economic_summary(econ_gold)
            total_records += loader.load_fx_snapshot(fx_gold)

            finished_at = datetime.now(timezone.utc)
            loader.log_pipeline_run(
                run_id, started_at, finished_at, status, total_records,
                " | ".join(notes) if notes else "Full ETL run completed"
            )

    except Exception as e:
        status      = "FAILED"
        finished_at = datetime.now(timezone.utc)
        logger.error(f"PIPELINE | Run {run_id} FAILED: {e}")

        try:
            with DuckDBLoader() as loader:
                loader.log_pipeline_run(run_id, started_at, finished_at, status, 0, str(e))
        except Exception:
            pass

        raise

    duration = (finished_at - started_at).total_seconds()
    logger.info(f"{'='*60}")
    logger.info(f"PIPELINE | Run {run_id} complete in {duration:.1f}s")
    logger.info(f"PIPELINE | Status: {status} | Records loaded: {total_records}")
    logger.info(f"{'='*60}")

    return {
        "run_id":         run_id,
        "status":         status,
        "records_loaded": total_records,
        "duration_secs":  duration,
    }


def scheduled_run():
    """Wrapper for scheduled execution with error isolation."""
    try:
        run_pipeline()
    except Exception as e:
        logger.error(f"SCHEDULER | Pipeline run failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SA Economic Data Pipeline")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on a schedule every 6 hours instead of once",
    )
    args = parser.parse_args()

    if args.schedule:
        logger.info("SCHEDULER | Running pipeline every 6 hours. Press Ctrl+C to stop.")
        run_pipeline()  # Run immediately on start
        schedule.every(6).hours.do(scheduled_run)
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_pipeline()
