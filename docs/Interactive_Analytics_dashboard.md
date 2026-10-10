
# RIDE360 — Phase 4 Interactive Analytics Dashboard

## Objective

Build an interactive business intelligence dashboard on top of
the validated RIDE360 PostgreSQL analytical warehouse.

## Technology Stack

- Python 3.11
- PostgreSQL 16
- psycopg 3
- pandas
- Streamlit
- Plotly

## Architecture

Source CSV
    |
    v
Phase 2 PostgreSQL Warehouse
    |
    v
Phase 3 Analytical SQL Views
    |
    v
dashboard_data.py
    |
    v
Streamlit + Plotly Dashboard

The dashboard queries analytical views only.

It does not update warehouse tables.

## Dashboard Pages

### Overview

- Executive KPIs
- Peak booking hour
- Peak booking month
- Highest-volume vehicle
- Highest-volume pickup
- Monthly booking trends

### Demand

- Daily booking demand
- Monthly booking demand
- Hourly demand
- Weekday demand
- Weekday-hour heatmap

### Cancellations

- Customer vs driver cancellations
- Cancellation reasons
- No-driver-found risk by hour

### Vehicles

- Booking volume
- Completed bookings
- Completed booking value
- Completion rates

### Locations

- Top pickup locations
- Top directional routes

### Customers

- Customer booking-frequency segments

## Interactive Features

- Ingestion batch selection
- Daily/monthly demand selection
- Cancellation actor selection
- Vehicle KPI selection
- Top N location selection
- Cached database queries
- Manual cache refresh
- CSV export

## Database Security

Dashboard data access uses:

- An explicit view allowlist
- Parameterized batch IDs
- Read-only PostgreSQL transactions

For production deployment, use a dedicated PostgreSQL
read-only account with SELECT permissions limited to
the required analytical and audit views.

Do not commit .env or database credentials.

## Run Locally

From the project root:

```powershell
python -m pip install -r requirements-dashboard.txt
```

Start PostgreSQL if needed:

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d
```

Launch the dashboard:

```powershell
python -m streamlit run dashboard/app.py
```

Open:

http://localhost:8501

## Testing

```powershell
python -m pytest -q tests/test_dashboard_data.py
python -m pytest -q
python -m ruff check .
```

## Data Quality Expectations

Batch 1:

- Booking records: 150,000
- Completed bookings: 93,000
- Cancelled bookings: 37,500
- Completion rate: 62.00%
- Cancellation rate: 25.00%
- Phase 3 SQL quality checks: 18/18 PASS

## Important Business Definitions

Booking records are source rows.

Booking ID is not unique and must not be treated
as a primary key.

Completed booking value is provisional and
must not be labeled recognized revenue.

Currency is not independently verified.

Customer ID is a source identifier and does not
establish verified personal identity.

No Driver Found is separate from cancellations.

Booking timestamps have no verified timezone.

The source covers 2024-01-01 through 2024-12-30.

## Deployment Notes

The local dashboard requires a running PostgreSQL
warehouse populated with Phase 2 and Phase 3 views.

Deploying Streamlit alone does not deploy PostgreSQL.

For cloud hosting:

1. Provision a reachable PostgreSQL instance.
2. Deploy the warehouse schemas and SQL views.
3. Load and validate the source data.
4. Create a restricted read-only database account.
5. Configure credentials using deployment secrets.
6. Configure network access and TLS.
7. Deploy the Streamlit application.
8. Run reconciliation and smoke tests.

The local development configuration is not a
production deployment configuration.

## Completion Criteria

- Dependencies installed
- Dashboard connects to PostgreSQL
- Executive KPI values reconcile
- All six tabs render
- Filters work
- CSV exports work
- Unit tests pass
- Full regression suite passes
- Ruff passes
- Git working tree clean
