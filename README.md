
# RIDE360 | Urban Mobility Analytics & Intelligence Platform

### From 150,000 Ride Bookings to Actionable Business Intelligence

An end-to-end **Analytics Engineering and Business Intelligence portfolio project** that transforms raw ride-booking records into a structured PostgreSQL data warehouse, reusable SQL analytics, interactive Streamlit and Power BI reporting, and a containerized analytics application.

**Python • PostgreSQL 16 • Advanced SQL • Pandas • Power BI • DAX • Streamlit • Plotly • Docker • GitHub Actions**

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

The solution combines reproducible data pipelines, analytical SQL, data-quality controls, interactive visualizations, executive BI reporting, and deployment engineering.

**Project deliverables:** PostgreSQL analytics warehouse · Streamlit analytics portal · six-page Power BI executive report (user-reported complete) · CEO strategic business report · Docker application · automated CI.

> **Portfolio scope:** RIDE360 is an analytics portfolio project using a historical booking dataset. It is not presented as a live operating company, and its recommendations have not been experimentally validated.

## Key Business Metrics

| Metric | Observed Value |
|---|---:|
| Total booking records | 150,000 |
| Completed bookings | 93,000 |
| Completion rate | 62.0% |
| Customer cancellations | 10,500 |
| Driver cancellations | 27,000 |
| Total cancellations | 37,500 |
| Total cancellation rate | 25.0% |
| Driver share of cancellations | 72.0% |
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
Historical ride-booking dataset (150,000 records)
                   |
                   v
Python validation + idempotent ingestion + batch reconciliation
                   |
                   v
PostgreSQL 16 warehouse
   |-- ride360_raw       (lossless source records)
   |-- ride360_staging   (standardized records)
   |-- ride360_analytics (SQL business views and marts)
   |-- ride360_audit     (batch and quality checks)
                   |
                   v
Business metrics + demand / cancellation / vehicle / location views
                   |
          +--------+------------------+
          |                           |
          v                           v
16 materialized cache views     Power BI Desktop
          |                     executive intelligence
          v                           |
Streamlit + Plotly portal       Six-page business report
          |
Dockerized local application
          |
GitHub Actions: lint, selected tests and Docker build
```

**Architecture note:** Power BI connects to PostgreSQL analytical views; the 16 cached materialized views primarily support the Streamlit analytics access layer. Docker and CI are engineering components, not proof of public hosting.

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data processing | Python, Pandas | Data ingestion and preparation |
| Database | PostgreSQL 16 | Analytical warehouse |
| Transformation | SQL | Reusable business logic and marts |
| Analytics acceleration | PostgreSQL materialized views | Cached dashboard queries |
| Visualization | Streamlit, Plotly | Interactive analytical dashboard |
| Executive BI | Power BI Desktop, Power Query, DAX | Six-page executive reporting and scenario analysis |
| Testing | Pytest, Ruff | Automated testing and code quality |
| Deployment | Docker, Docker Compose | Reproducible application environment |
| CI | GitHub Actions | Automated lint, selected unit tests, Docker build |
| Business documentation | CEO strategic report | Executive findings, recommendations, technical assessment |

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

The Streamlit interface can be launched locally. Add verified Streamlit screenshots here when committed to the repository.

## Power BI | Executive Intelligence Suite

### Six Pages of Executive and Operational Intelligence

The Power BI report complements the Streamlit analytics portal with an executive-facing narrative and an interactive business improvement scenario. Its six pages were completed according to the project owner's latest update; the actual `.pbix` and exported screenshots have not been independently audited here.

| Page | Executive question | Primary analysis |
|---|---|---|
| 01 — Executive Overview | How is the platform performing? | Booking volume, completion, cancellations, completed booking value and monthly trends |
| 02 — Cancellation Intelligence | Where does service reliability break down? | Driver/customer cancellations, reasons and monthly patterns |
| 03 — Demand & Capacity | When does demand concentrate? | Hourly demand, weekday-hour heatmap, dayparts and service risk |
| 04 — Vehicle Performance | Which categories drive demand? | Vehicle mix and monthly vehicle trends |
| 05 — Location Intelligence | Which locations and routes matter most? | Pickup hotspots, route demand and service outcomes |
| 06 — Strategy & Recommendations | What should leadership test next? | Priority actions and a hypothetical cancellation-reduction scenario |

**BI techniques:** PostgreSQL import, Power Query type validation, DAX measures, KPI cards, time-series visualizations, matrices with conditional formatting, page navigation and what-if scenario analysis. Aggregated SQL views are handled at their respective grains rather than being indiscriminately joined.

### Power BI Business Findings

- **Completion:** 93,000 of 150,000 booking records completed (**62.0%**).
- **Cancellations:** 37,500 bookings cancelled (**25.0%**); 27,000 were driver cancellations (**72.0% of cancellations**).
- **Peak hour:** 18:00, with 12,397 booking records.
- **Peak month:** July 2024, with 12,897 booking records.
- **Leading vehicle category:** Auto, with 37,419 bookings.
- **Leading pickup location:** Khandsa, with 949 bookings.
- **Completed booking value:** 47,260,574 in dataset units; currency and revenue recognition are unverified.

### Report Assets and Screenshots

Expected local report structure (add actual exported files to GitHub before linking them as downloadable assets):

```text
reports/powerbi/
|-- RIDE360_Intelligence.pbix          # Editable report; typically attached to a GitHub Release
|-- RIDE360_Theme.json                # Executive dark theme
|-- RIDE360_Executive_Report.pdf      # Exported six-page BI report
|-- screenshots/
|   |-- 01_executive_overview.png
|   |-- 02_cancellation_intelligence.png
|   |-- 03_demand_capacity.png
|   |-- 04_vehicle_performance.png
|   |-- 05_location_intelligence.png
|   `-- 06_strategy_recommendations.png
```

**Preview:** Once the screenshots are committed, add the Executive Overview image at the top of this README and link the remaining five pages. The `.pbix` is excluded by the existing Git ignore rules; publish it as a reviewed GitHub Release asset if distribution is appropriate. Power BI Import files may contain embedded data and connection information.

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
|   |-- powerbi/           # Power BI theme, report exports and screenshots
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

## Business Strategy and CEO Recommendations

### Evidence-Based Operational Priorities

| Priority | Observed evidence | Recommended management action | Success metric |
|---|---|---|---|
| 1 — Driver reliability | 27,000 driver cancellations; 72% of cancellations | Segment driver cancellations by hour, area and category; pilot dispatch or acceptance improvements | Driver cancellation rate |
| 2 — Peak-period readiness | 18:00 is the highest-volume booking hour | Compare demand with verified supply availability; test targeted capacity changes | Completion rate and no-driver-found rate during pilot hours |
| 3 — Location operations | Khandsa leads pickup volume at 949 records | Review hotspot fulfillment and service-risk patterns | Location-level completion and service failure rates |
| 4 — Vehicle mix | Auto leads at 37,419 bookings | Review category-specific demand and operational outcomes | Vehicle-level completion and cancellation rates |
| 5 — Reporting governance | Historical data across several analytical grains | Set a weekly KPI review with documented definitions and source reconciliation | Data-quality pass rate and consistent KPI reporting |

### Cancellation-Reduction Scenario — Not an Achieved Result

Holding historical booking volume fixed at **150,000**:

| Metric | Baseline | Hypothetical target |
|---|---:|---:|
| Cancellation rate | 25% | 20% |
| Cancellation count | 37,500 | 30,000 |
| Potential avoided cancellations | — | **7,500** |

The target is a **5-percentage-point absolute reduction**, or a **20% relative reduction in cancellations**. This is a planning calculation only: no pilot, causal impact, incremental completed rides, revenue uplift or cost savings have been demonstrated.

### CEO Strategic Report

A separate **15-page CEO strategic business and technical report** has been prepared, covering the operating funnel, customer and location intelligence, opportunities, warehouse architecture, testing, deployment and a proposed operational roadmap. Add its final PDF to `reports/` and link it here once committed to the repository. This document is a portfolio briefing, not an audited financial report.

## Roadmap

- [x] Data profiling and source-quality analysis
- [x] PostgreSQL analytical warehouse
- [x] SQL analytics and business intelligence
- [x] Interactive Streamlit dashboard
- [x] Materialized analytics cache
- [x] Docker deployment configuration
- [x] GitHub Actions CI
- [x] Power BI executive reporting (completed as reported; final file review pending)
- [x] Business-impact case study and CEO strategic briefing (scenario-based)
- [ ] Expanded database integration testing in CI
- [ ] Verify and publish final Power BI PDF, screenshots and GitHub Release asset

## Power BI and CEO Report Publishing Checklist

1. Confirm the `.pbix` opens and all six pages show correct values.
2. Export the Power BI PDF and six real screenshots into `reports/powerbi/`.
3. Verify no sensitive information is included in shared report files.
4. Commit the theme, PDF and screenshots; attach the `.pbix` to a GitHub Release if appropriate.
5. Add verified asset links and a real executive dashboard screenshot to this README.
6. Publish the 15-page CEO PDF in the repository only after confirming the final report version.

## Engineering Principles

RIDE360 emphasizes:

- **Data integrity:** Preserve source records and explicitly handle duplicate business identifiers.
- **Reproducibility:** Keep transformations, tests, and deployment configuration in version control.
- **Performance:** Separate analytical consumption from expensive source-view computation.
- **Security:** Use read-only database access for dashboard queries.
- **Business clarity:** Distinguish observed metrics from estimates, assumptions, and scenarios.

## Author

**Aditya Sharma**

---

*RIDE360 — Turning urban mobility data into operational intelligence.*
