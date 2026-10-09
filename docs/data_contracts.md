
# RIDE360 — Source Data & KPI Contracts

Version: 1.0  
Dataset: rideBookings.csv  
Source period: 2024  
Contract grain: Source CSV row

## 1. Source Grain

One source row represents one reported booking record.

Booking ID is not unique in the source.

Observed baseline:
- Source records: 150,000
- Distinct non-null Booking IDs: 148,767
- Repeated-ID groups: 1,224
- Repeated-ID conflict groups: 1,224

Do not deduplicate or overwrite conflicting records without an
approved source-of-truth policy.

## 2. Data Dictionary

The authoritative, machine-readable dictionary is defined in:

`src/ride360/metadata.py`

Generated CSV:

`reports/generated/metadata/data_dictionary.csv`

The dictionary covers all 21 source columns and records:
- Column name
- Logical data type
- Null policy
- Business description
- Analytical role

### Null Policy Definitions

- required: Expected for every record.
- conditional: Expected according to booking status or event type.
- review: Business meaning and null requirements need confirmation.

### Conditional Event Fields

For Cancelled by Customer:
- Cancelled Rides by Customer must equal 1.
- Reason for cancelling by Customer must be present.

For Cancelled by Driver:
- Cancelled Rides by Driver must equal 1.
- Driver Cancellation Reason must be present.

For Incomplete:
- Incomplete Rides must equal 1.
- Incomplete Rides Reason must be present.

Outside their corresponding statuses, these event flags and reasons
are expected to be absent.

## 3. KPI Contracts

The machine-readable KPI contract is defined in:

`src/ride360/metadata.py`

Generated CSV:

`reports/generated/metadata/kpi_contracts.csv`

### Approved Record-Grain Metrics

Booking Records:
Count all source rows.

Distinct Booking IDs:
Count distinct non-null Booking ID values.
This is an identifier count, not an approved deduplicated
booking-fact count.

Completed Records:
Count rows where Booking Status equals Completed.

Completion Rate:
Completed Records / Booking Records * 100.

Customer Cancellation Rate:
Customer-cancelled records / Booking Records * 100.

Driver Cancellation Rate:
Driver-cancelled records / Booking Records * 100.

Overall Cancellation Rate:
(Customer-cancelled records + Driver-cancelled records)
 / Booking Records * 100.

Incomplete Rate:
Incomplete records / Booking Records * 100.

No Driver Found Rate:
No-driver-found records / Booking Records * 100.

For zero denominator, rates return null rather than zero.

### Provisional Monetary Metric

Completed Booking Value:
Sum numeric Booking Value for Completed source records.

This is NOT approved as realized revenue, collected fare,
gross merchandise value, or platform commission.

Currency and refund/settlement semantics require confirmation.

## 4. Source Statuses

Known values:
- Completed
- Cancelled by Customer
- Cancelled by Driver
- No Driver Found
- Incomplete

Do not silently map unknown statuses to existing categories.

## 5. Unresolved Business Questions

1. What is the authoritative source-record grain?
2. Why do Booking IDs repeat with conflicting attributes?
3. Which record should represent a booking if a booking-grain
   fact table is required?
4. What currency is Booking Value expressed in?
5. Is Booking Value a quoted fare, charged amount, or other value?
6. What units are used for Ride Distance, Avg VTAT and Avg CTAT?
7. Are ratings collected only after completed rides?
8. Are payment methods proof of successful payment?

## 6. Validation Policy

Raw source files are immutable.

Quality warnings must remain visible in reporting.

No record is removed automatically.

Metric definitions must be reused consistently across Python,
PostgreSQL, Excel and Power BI.

Source-record KPIs are approved for descriptive analysis.
Booking-grain metrics remain provisional until duplicate
conflicts are resolved.
