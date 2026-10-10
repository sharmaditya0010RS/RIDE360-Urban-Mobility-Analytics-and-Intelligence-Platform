# RIDE360 — Deployment and Operations

## Architecture

RIDE360 uses PostgreSQL 16 for the analytical warehouse, Python for ingestion and transformation, and Streamlit for the analytics portal.

A materialized analytics cache accelerates dashboard queries while retaining the original SQL views as authoritative sources.

## Local development

Activate the Python 3.11 environment and run:

```powershell
python -m streamlit run dashboard/app.py
```

## Build analytics cache

```powershell
python -m ride360.analytics_cache build
```

Refresh after new warehouse data is validated:

```powershell
python -m ride360.analytics_cache refresh
```

## Verify data consistency

```powershell
python scripts/verify_analytics.py --batch 1
```

For full verification including expensive quality checks, use `--include-quality`.

## Performance benchmark

```powershell
python scripts/benchmark_analytics.py --mode cached
```

Benchmark results are stored under `reports/exports/`.

## Container deployment

Configure database connectivity and secrets before starting the container.

```powershell
docker compose build
docker compose up -d
docker compose ps
```

Open `http://localhost:8501`.

## Security

Use a dedicated read-only PostgreSQL account for the dashboard. Never commit `.env` or credentials. Cache refresh must use a separate account with the required refresh permissions.

## Operational checks

- Verify the dashboard health endpoint.
- Confirm the selected warehouse batch exists in the cache.
- Check cache freshness after each ingestion.
- Monitor failed refresh operations.
- Re-run data consistency checks before promoting a refreshed cache.
- Retain original SQL views for auditability and recovery.

## Recovery

If cache validation fails, disable cache reads and use the authoritative analytical views. Do not delete source warehouse tables or validated views.

## Data interpretation

Booking IDs are not guaranteed unique. Completed booking value is not equivalent to verified recognized revenue. Power BI reports should only be published or downloaded when real report assets exist.
