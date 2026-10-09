
# RIDE360 — Phase 3 Analytics Engineering

## 1. Objective

Phase 3 builds advanced business analytics on top of the
validated Phase 2 PostgreSQL warehouse.

Core capabilities:

- Validated booking dates and times
- Daily and monthly demand analysis
- Weekday and hourly booking patterns
- Peak-hour demand intelligence
- Customer and driver cancellation analytics
- Vehicle performance by month
- Pickup and route demand analysis
- Customer booking-frequency segmentation
- Executive business insights
- Cross-mart quality reconciliation

## 2. Dependencies

Phase 3 depends on the completed Phase 2 warehouse.

Required schemas:

- ride360_raw
- ride360_staging
- ride360_analytics
- ride360_audit

Required Phase 2 source data:

150,000 booking records, Batch 1.

## 3. Phase 3 SQL Files

| File | Purpose |
|---|---|
| temporal_transformations.sql | Safe temporal conversion |
| demand_analytics.sql | Daily, monthly, hourly demand |
| operational_analytics.sql | Cancellations and vehicles |
| customer_location_analytics.sql | Customers, pickups, routes |
| business_insights.sql | Executive insights and checks |

## 4. Temporal Model

Source date format:

YYYY-MM-DD

Source time format:

HH:MM:SS, 24-hour clock.

Calendar and clock validity are checked before conversion.

The temporal staging view preserves the original
raw_record_id and source-record grain.

Temporal dimensions include:

- booking_date
- booking_time
- booking_timestamp
- booking_year
- booking_month
- booking_quarter
- booking_iso_weekday
- booking_hour
- booking_month_start
- booking_week_start
- booking_daypart

The timestamp is timezone-naive.

No timezone is inferred from the source.

## 5. Demand Analytics

Analytical views:

- daily_booking_trends
- monthly_booking_trends
- weekday_booking_demand
- hourly_booking_demand
- daypart_booking_demand
- weekday_hour_heatmap

Every booking belongs to one daily, monthly, weekday,
hourly and daypart grouping when its temporal fields
are valid.

The heatmap uses ISO weekday numbering:

Monday = 1, Sunday = 7.

## 6. Operational Intelligence

Views:

- monthly_cancellation_intelligence
- hourly_service_risk
- monthly_vehicle_intelligence
- cancellation_reason_intelligence

Cancellation actor categories:

- Customer
- Driver

Missing cancellation reasons are labeled Unspecified.

Cancellation rates use all booking records in the
relevant group as the denominator.

No Driver Found is tracked separately from cancellations.

## 7. Customer and Location Intelligence

Views:

- customer_booking_activity
- customer_frequency_segments
- pickup_demand_intelligence
- route_demand_intelligence

Customer ID is treated as a source identifier.

Booking ID is not used as a unique trip key.

Frequency segments:

- 1 booking
- 2-4 bookings
- 5-9 bookings
- 10+ bookings

Records with missing Customer IDs are excluded from
customer-specific aggregates but remain in overall
booking, vehicle, pickup and route metrics.

Pickup and drop location names are treated as source
labels. No geocoding is performed.

Routes are directional.

## 8. Executive Insights

The business_insight_summary view provides:

- Total bookings
- Completed bookings
- Cancelled bookings
- Completion and cancellation rates
- Completed booking value
- Peak booking hour
- Peak booking month
- Highest-volume vehicle
- Highest-volume pickup location

These metrics describe observed source data.

They do not establish causality.

Completed booking value is not confirmed realized revenue.

## 9. Verified Observations

Based on the Phase 3.3 query outputs:

- Total booking records: 150,000
- Peak month: July 2024
- July bookings: 12,897
- Peak hour: 18:00-18:59
- Peak-hour bookings: 12,397
- Monthly records reconcile to 150,000
- Hourly records reconcile to 150,000
- All six demand marts reconcile to 150,000

Additional operational, customer and location findings
should be documented after the corresponding SQL
queries are executed and validated.

## 10. Data Quality

Phase 3 quality checks reconcile:

- Raw and temporal records
- Valid and invalid timestamp partitions
- Daily and monthly demand
- Hourly and weekday demand
- Daypart demand
- Weekday-hour heatmap
- Monthly cancellation counts
- Monthly vehicle counts
- Completed booking value
- Pickup and route counts
- Cancellation reason totals
- Known customer activity
- Customer frequency segments

Quality views:

- ride360_audit.phase3_quality_checks
- ride360_audit.phase3_quality_summary

Any failed check must be investigated before marking
Phase 3 complete.

## 11. Execution Order

Run from the project root with PostgreSQL running.

### Temporal transformations

```powershell
Get-Content sql/temporal_transformations.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Demand analytics

```powershell
Get-Content sql/demand_analytics.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Operational analytics

```powershell
Get-Content sql/operational_analytics.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Customer and location analytics

```powershell
Get-Content sql/customer_location_analytics.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### Business insights

```powershell
Get-Content sql/business_insights.sql -Raw |
    docker exec -i ride360_postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## 12. Verification

```sql
SELECT *
FROM ride360_audit.phase3_quality_summary
ORDER BY batch_id;
```

Expected for Batch 1 after all checks pass:

- Total checks: 18
- Passed checks: 18
- Failed checks: 0
- All checks passed: true

Run tests:

```powershell
python -m pytest -q
```

Run lint:

```powershell
python -m ruff check .
```

## 13. Known Limitations

- Source data covers 2024-01-01 through 2024-12-30.
- December 31 is not present in the observed source range.
- Timezone is not verified.
- Booking ID is not unique.
- Customer ID does not establish verified personal identity.
- Location names are not geocoded.
- Completed booking value is not recognized revenue.
- Currency and distance units remain unverified.
- Analytics use SQL views rather than materialized tables.
- No causal claims should be inferred from observed patterns.
- Additional production work would be needed for
  incremental refresh, access controls and monitoring.

## 14. Phase 3 Completion Criteria

Phase 3 is complete when:

1. All SQL files execute successfully.
2. Temporal validity checks pass.
3. Demand marts reconcile.
4. Operational and location marts reconcile.
5. Phase 3 quality checks pass.
6. Integration tests pass.
7. Full regression suite passes.
8. Ruff passes.
9. Documentation is committed.
10. Git working tree is clean.
```
