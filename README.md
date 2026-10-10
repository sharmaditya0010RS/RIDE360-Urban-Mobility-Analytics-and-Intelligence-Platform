
# RIDE360 | Urban Mobility Intelligence Platform

### From 150,000 Ride Bookings to Actionable Business Intelligence

An end-to-end **Analytics Engineering and Business Intelligence portfolio project** that transforms raw ride-booking records into a structured PostgreSQL data warehouse, reusable SQL analytics, an interactive Streamlit dashboard, and a containerized analytics application.

**Python • PostgreSQL • SQL • Pandas • Streamlit • Plotly • Docker • GitHub Actions**

[![CI](https://github.com/sharmaditya0010RS/Ride360-URBAN-MOBILITY-INTELLIGENCE-PLATFORM/actions/workflows/ci.yml/badge.svg)](https://github.com/sharmaditya0010RS/Ride360-URBAN-MOBILITY-INTELLIGENCE-PLATFORM/actions)

---

## Executive Summary

RIDE360 explores the operational performance of an urban ride-booking platform using **150,000 booking records**.

The project addresses five business questions:

1. How effectively does booking demand convert into completed rides?
2. Where are cancellations and service failures concentrated?
3. When does demand peak, and what does that imply for capacity planning?
4. How do vehicle categories and locations differ in performance?
5. Which operational improvements should be prioritized?

The solution combines reproducible data pipelines, analytical SQL, data-quality controls, interactive visualizations, and deployment engineering.

## Key Business Metrics

| Metric | Observed Value |
|---|---:|
| Total booking records | 150,000 |
| Completed bookings | 93,000 |
| Completion rate | 62.0% |
| Customer cancellations | 10,500 |
| Driver cancellations | 27,000 |
| Total cancellation rate | 25.0% |
| Incomplete rides | 9,000 |
| No driver found | 10,500 |
| Completed booking value | 47,260,574 |

**Important:** Completed booking value is a dataset-reported monetary measure, not verified recognized revenue. Currency and financial recognition rules have not been independently established.

### Initial Business Findings

- **Driver cancellations are the largest cancellation category**, representing 27,000 booking records.
- **18:00 is the peak booking hour**, with 12,397 bookings.
- **July records the highest monthly demand**, with 12,897 bookings.
- **Auto is the most frequent vehicle category**, with 37,419 bookings.
- **Khandsa is the highest-volume pickup location**, with 949 bookings.

These findings identify opportunities for cancellation analysis, capacity planning, and location-level operational monitoring. They do not, by themselves, establish causation.

## Platform Architecture

```text
Raw Ride-Booking Dataset
          |
          v
Python Data Ingestion
          |
          v
PostgreSQL Data Warehouse
  |-- Raw Layer
  |-- Staging Layer
  |-- Analytics Layer
  |-- Audit Layer
          |
          v
SQL Transformations & Business Marts
          |
          v
16 Materialized Analytics Views
          |
          v
Streamlit + Plotly Dashboard
          |
          v
Dockerized Local Deployment
          |
          v
GitHub Actions CI
```

The platform separates ingestion, transformation, analytical consumption, and quality verification.

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data processing | Python, Pandas | Data ingestion and preparation |
| Database | PostgreSQL 16 | Analytical warehouse |
| Transformation | SQL | Reusable business logic and marts |
| Analytics acceleration | PostgreSQL materialized views | Cached dashboard queries |
| Visualization | Streamlit, Plotly | Interactive analytical dashboard |
| Testing | Pytest, Ruff | Automated testing and code quality |
| Deployment | Docker, Docker Compose | Reproducible application environment |
| CI | GitHub Actions | Automated lint, selected unit tests, Docker build |
| Planned BI extension | Power BI | Executive reporting and business-impact case study |

## Interactive Analytics Dashboard

The Streamlit application provides seven analytical sections:

| Page | Analytical Focus |
|---|---|
| Overview | Executive KPIs and platform performance |
| Demand | Booking volume, time patterns, and peak periods |
| Cancellations | Cancellation trends and operational risks |
| Vehicles | Vehicle-category performance |
| Locations | Pickup demand and route intelligence |
| Customers | Customer frequency and behavior segments |
| Report Center | Access to generated reports and documentation |

### Dashboard Screenshots

Dashboard screenshots will be added to the repository as the presentation layer is finalized.

## Data Engineering and Quality

### Warehouse Design

The PostgreSQL warehouse organizes data into four logical schemas:

- `ride360_raw` — lossless source ingestion
- `ride360_staging` — cleaned and standardized records
- `ride360_analytics` — analytical views and business marts
- `ride360_audit` — data-quality checks and audit outputs

### Important Data Integrity Decision

Booking IDs are not guaranteed to be unique in the source data.

The dataset contains:

- 148,767 distinct booking IDs
- 1,224 repeated-ID groups
- 2,457 rows belonging to repeated-ID groups

RIDE360 preserves these source records and uses a surrogate identifier in the raw warehouse layer rather than incorrectly treating the booking ID as a unique primary key.

### Validation

The project includes:

- Schema and business-rule validation
- Warehouse quality checks
- Analytical consistency checks
- Automated Python tests
- Materialized-view source-to-cache comparisons

**16 of 16 materialized analytics views passed source-to-cache verification.**

## Analytics Performance

The dashboard supports cached analytical queries through PostgreSQL materialized views.

Performance measurements from the local benchmark include:

| Query Type | Observed Cached Query Time |
|---|---:|
| Typical analytical queries | Approximately 0.04–0.16 seconds |
| Route intelligence query | Approximately 0.73 seconds |
| Quality summary query | Approximately 0.05 seconds |

These are local benchmark observations, not guaranteed production performance.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop
- PostgreSQL 16 or a compatible PostgreSQL instance
- PowerShell or a compatible terminal

### Clone the Repository

```bash
git clone https://github.com/sharmaditya0010RS/Ride360-URBAN-MOBILITY-INTELLIGENCE-PLATFORM.git
cd Ride360-URBAN-MOBILITY-INTELLIGENCE-PLATFORM
```

### Install Dependencies

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project and dashboard dependencies:

```bash
python -m pip install -e .
python -m pip install -r requirements-dashboard.txt
python -m pip install pytest ruff
```

### Database Configuration

Create a local `.env` file with the database settings appropriate for your PostgreSQL instance.

```dotenv
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=ride360
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

**Never commit credentials or `.env` files.**

The dashboard requires an initialized RIDE360 warehouse with the corresponding analytical views or materialized views. The raw source dataset is not distributed in this repository.

### Run the Dashboard Locally

```powershell
$env:RIDE360_USE_CACHE = "1"
python -m streamlit run dashboard/app.py
```

Open:

http://localhost:8501

### Docker Deployment

A Dockerfile and Docker Compose configuration are included.

The Compose setup expects a local `.env.dashboard` containing database credentials and an accessible PostgreSQL warehouse.

```bash
docker compose build dashboard
docker compose up -d dashboard
docker compose ps
```

Open:

http://localhost:8501

See `docs/deployment.md` for deployment-specific details.

**Note:** This is a local Docker deployment workflow, not a publicly hosted dashboard.

## Testing and CI

Run static checks:

```bash
python -m ruff check .
```

Run the selected database-independent unit test suite:

```bash
python -m pytest -q \
  tests/test_business_rules.py \
  tests/test_cli.py \
  tests/test_dashboard_data.py \
  tests/test_event_rules.py \
  tests/test_metadata.py \
  tests/test_phase1.py \
  tests/test_profiling.py \
  tests/test_quality.py \
  tests/test_report_catalog.py
```

The selected suite passed **85 tests** in local verification.

GitHub Actions currently runs:

- Lint and selected unit tests
- Docker image build

Database-dependent integration tests require a configured warehouse and are not part of the current GitHub Actions checks.

## Project Structure

```text
RIDE360/
|
|-- .github/workflows/      # CI pipeline
|-- dashboard/              # Streamlit application
|   |-- assets/             # Dashboard styling
|   |-- pages/              # Analytical dashboard pages
|
|-- data/                   # Local data directories
|-- docs/                   # Engineering and deployment docs
|-- reports/                # Reports and project inventory
|-- scripts/                # Benchmarking and verification
|-- sql/                    # Warehouse and analytical SQL
|-- src/ride360/            # Python application package
|-- tests/                  # Automated tests
|
|-- Dockerfile
|-- compose.yaml
|-- pyproject.toml
|-- requirements-dashboard.txt
|-- README.md
```

## Business Impact: Scenario Analysis

The observed cancellation rate is **25%**.

A hypothetical reduction to **20%**, holding booking volume constant, would imply:

- Current cancellations: 37,500
- Scenario cancellations: 30,000
- Potential reduction: 7,500 cancellations

This is a **planning scenario, not an achieved result**. Actual business impact would require an operational intervention, controlled measurement, and appropriate financial assumptions.

## Roadmap

- [x] Data profiling and source-quality analysis
- [x] PostgreSQL analytical warehouse
- [x] SQL analytics and business intelligence
- [x] Interactive Streamlit dashboard
- [x] Materialized analytics cache
- [x] Docker deployment configuration
- [x] GitHub Actions CI
- [ ] Power BI executive reporting
- [ ] Business-impact case study
- [ ] Expanded database integration testing in CI
- [ ] Portfolio screenshots and presentation assets

## Engineering Principles

RIDE360 emphasizes:

- **Data integrity:** Preserve source records and explicitly handle duplicate business identifiers.
- **Reproducibility:** Keep transformations, tests, and deployment configuration in version control.
- **Performance:** Separate analytical consumption from expensive source-view computation.
- **Security:** Use read-only database access for dashboard queries.
- **Business clarity:** Distinguish observed metrics from estimates, assumptions, and scenarios.

## Author

**Aditya Sharma**

GitHub: [sharmaditya0010RS](https://github.com/sharmaditya0010RS)

---

*RIDE360 — Turning urban mobility data into operational intelligence.*
