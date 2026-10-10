# Phase 5 — Performance, deployment and monitoring

## Baseline first

Run `python scripts/benchmark_dashboard.py` while PostgreSQL is running. This records the execution time and row count for each allowlisted analytical view in `reports/exports/dashboard_benchmark.json`. It is **not** an EXPLAIN plan and it does not prove an index will help.

Next steps:

1. Review slowest views and obtain `EXPLAIN (ANALYZE, BUFFERS)` for representative queries.
2. Evaluate materialized views or summary tables only where query cost warrants them; define refresh cadence and stale-data notices.
3. Add a separate PostgreSQL read-only login for deployed dashboards.
4. Dockerize the Streamlit app, use secrets rather than committed `.env`, and add health checks.
5. Add dashboard page smoke tests, CI and report artifact publishing workflow.
6. Verify reports contain no sensitive data before publishing.

**Not implemented yet:** production Docker deployment, scheduled refresh, monitoring/alerting or CI. This file and benchmark script start Phase 5; they do not complete it.
