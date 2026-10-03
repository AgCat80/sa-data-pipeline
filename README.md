# SA Economic Data Pipeline 🇿🇦

A real-world data engineering project that builds a fully automated ETL pipeline for South African economic data. Pulls from public APIs, transforms data through the **medallion architecture** (Bronze → Silver → Gold), stores it in a local analytical data warehouse, and displays it on an interactive dashboard.

Built by **Gulian Ibrahim** as a data engineering portfolio project.

---

## Live Dashboard Preview

```
SA Economic Data Pipeline
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ GDP (USD)   │ GDP Growth  │ Inflation   │ Unemployment│
│ $405B       │ 1.94%       │ 5.87%       │ 32.9%       │
└─────────────┴─────────────┴─────────────┴─────────────┘
  📈 Trends    💱 FX Rates   🏥 Health Score  🔧 Pipeline
```

---

## What This Project Demonstrates

| Concept | Implementation |
|---------|---------------|
| ETL Pipeline | Extract → Transform → Load in modular stages |
| Medallion Architecture | Bronze (raw) → Silver (clean) → Gold (analytics-ready) |
| Data Ingestion | REST API calls with pagination and error handling |
| Data Transformation | Pandas — cleaning, pivoting, rolling averages, composite scores |
| Data Warehouse | DuckDB — columnar analytical database with SQL queries |
| Orchestration | Schedule-based pipeline runner with logging and run history |
| Data Visualisation | Streamlit + Plotly interactive dashboard |
| Data Quality | Null handling, type casting, schema validation, deduplication |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                         │
│  Open Exchange Rates API  │  World Bank Open Data API   │
└──────────────┬────────────┴────────────┬────────────────┘
               │ HTTP REST                │ HTTP REST
               ▼                          ▼
┌─────────────────────────────────────────────────────────┐
│               BRONZE LAYER  (Raw Storage)               │
│  Raw JSON files saved to /data/bronze/                  │
│  Exact copy of API response + ingestion metadata        │
└──────────────────────────┬──────────────────────────────┘
                           │ Pandas transform
                           ▼
┌─────────────────────────────────────────────────────────┐
│               SILVER LAYER  (Clean Storage)             │
│  Typed, validated, normalised Parquet files             │
│  Nulls removed · Columns cast · YoY change derived     │
└──────────────────────────┬──────────────────────────────┘
                           │ Aggregation + enrichment
                           ▼
┌─────────────────────────────────────────────────────────┐
│               GOLD LAYER  (Analytics-Ready)             │
│  Rolling averages · Economic health score · FX snapshot │
│  Parquet files ready for warehouse load                 │
└──────────────────────────┬──────────────────────────────┘
                           │ DuckDB INSERT
                           ▼
┌─────────────────────────────────────────────────────────┐
│               DUCKDB WAREHOUSE                          │
│  economic_summary │ fx_snapshot │ pipeline_runs         │
└──────────────────────────┬──────────────────────────────┘
                           │ SQL queries
                           ▼
┌─────────────────────────────────────────────────────────┐
│               STREAMLIT DASHBOARD                       │
│  KPIs · Charts · FX Rates · Health Score · Run History  │
└─────────────────────────────────────────────────────────┘
```

---

## Data Sources

| Source | Data | API Docs |
|--------|------|----------|
| [Open Exchange Rates](https://open.er-api.com) | Live USD/ZAR and cross rates | Free, no key |
| [World Bank Open Data](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) | SA GDP, inflation, unemployment (2010–2024) | Free, no key |

---

## Project Structure

```
sa-data-pipeline/
├── extractors/
│   ├── exchange_rate_extractor.py   ← Pulls FX data (bronze)
│   └── world_bank_extractor.py      ← Pulls WB economic indicators (bronze)
├── transformers/
│   ├── silver_transformer.py        ← Cleans and validates raw data
│   └── gold_transformer.py          ← Builds analytics-ready aggregations
├── loaders/
│   └── duckdb_loader.py             ← Loads gold data into DuckDB warehouse
├── dashboard/
│   └── app.py                       ← Streamlit interactive dashboard
├── data/
│   ├── bronze/                      ← Raw API JSON files
│   ├── silver/                      ← Clean Parquet files
│   ├── gold/                        ← Aggregated Parquet files
│   └── sa_pipeline.duckdb           ← DuckDB analytical warehouse
├── pipeline.py                      ← Main ETL orchestrator
├── config.py                        ← Central configuration
├── requirements.txt
└── README.md
```

---

## Setup and Installation

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repo
git clone https://github.com/AgCat80/sa-data-pipeline.git
cd sa-data-pipeline

# Create a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Pipeline

### Run once (full ETL)
```bash
python pipeline.py
```

### Run on a schedule (every 6 hours)
```bash
python pipeline.py --schedule
```

### Launch the dashboard
```bash
streamlit run dashboard/app.py
```
Then open `http://localhost:8501` in your browser. Use the **Run Pipeline Now** button in the sidebar to trigger the ETL and populate the charts.

---

## Key Data Engineering Concepts Used

**Medallion Architecture** — Data flows through three quality tiers. Bronze stores raw API responses untouched. Silver stores clean, typed, validated data. Gold stores analytics-ready aggregates with derived metrics. This separation means raw data is always preserved and each transformation step is independently auditable.

**Parameterised Queries / No SQL Injection** — All DuckDB writes use parameterised statements rather than string interpolation.

**Idempotency** — Re-running the pipeline for the same date range replaces existing rows rather than duplicating them. Same input always produces the same output.

**Pipeline Run Logging** — Every pipeline run is logged to a `pipeline_runs` table in DuckDB with start time, end time, status, record count, and error details.

**Parquet Storage** — Silver and gold layers use Parquet format: columnar, compressed, and faster to read than CSV for analytical queries.

---

## Technologies

- **Python 3.10+** — Core language
- **DuckDB** — Embedded analytical SQL database (modern alternative to SQLite for analytics)
- **Pandas** — Data transformation and cleaning
- **Requests** — HTTP API calls
- **Streamlit** — Dashboard UI
- **Plotly** — Interactive charts
- **Loguru** — Clean structured logging
- **Schedule** — Lightweight pipeline scheduling

---

## Author

**Gulian Ibrahim** — Cape Town, South Africa  
Aspiring Data Engineer | BSc Computing @ STADIO  
GitHub: [AgCat80](https://github.com/AgCat80)  
LinkedIn: [gulian-ibrahim](https://www.linkedin.com/in/gulian-ibrahim)
