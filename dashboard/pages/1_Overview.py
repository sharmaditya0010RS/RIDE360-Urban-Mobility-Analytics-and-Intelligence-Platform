"""Executive command center."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (
    bar,
    cell,
    donut,
    first,
    frame,
    insight,
    line,
    metric,
    rate,
    section,
    setup_page,
    table,
    top,
)


def as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


batch = setup_page("Executive Pulse", "COMPANY PERFORMANCE  /  BOOKING OUTCOMES  /  QUALITY ASSURANCE")
kpis = frame("executive", batch)
if kpis.empty:
    st.warning("No KPI data available.")
    st.stop()
row = kpis.iloc[0]
bookings = as_float(cell(kpis, "total_booking_records", "total_bookings", default=0))
completed = as_float(cell(kpis, "completed_bookings", default=0))
cancelled = as_float(cell(kpis, "cancelled_bookings", default=0))
other = max(0, bookings - completed - cancelled)
cols = st.columns(4)
with cols[0]:
    metric("Booking records", bookings)
with cols[1]:
    metric("Completed", completed)
with cols[2]:
    metric("Completion rate", rate(completed, bookings), "%", 2)
with cols[3]:
    metric("Cancellation rate", rate(cancelled, bookings), "%", 2)
cols = st.columns(4)
with cols[0]:
    metric("Cancellations", cancelled)
with cols[1]:
    metric("Other outcomes", other)
with cols[2]:
    metric("Completed booking value", cell(kpis, "completed_booking_value_total", default=0), help_text="Source value; currency and revenue recognition not verified")
with cols[3]:
    metric("Ingestion batch", batch)
st.divider()
section("Executive interpretation", "An actionable reading of source-record outcomes")
left, right = st.columns(2)
with left:
    insight("Fulfillment baseline", f"{rate(completed, bookings):.1f}% of booking records completed. {other:,.0f} records have outcomes other than completed or customer/driver cancelled.")
with right:
    insight("Cancellation exposure", f"{cancelled:,.0f} records were cancelled ({rate(cancelled, bookings):.1f}% of all records). Compare actor and reason breakdowns on Service Reliability.")
outcomes = pd.DataFrame({"Outcome": ["Completed", "Cancelled", "Other"], "Records": [completed, cancelled, other]})
a, b = st.columns(2)
with a:
    donut(outcomes, "Outcome", "Records", "Outcome mix")
with b:
    bar(outcomes, "Outcome", "Records", "Outcome volumes")
section("Demand pulse")
monthly = frame("monthly", batch)
daily = frame("daily", batch)
a, b = st.columns(2)
with a:
    line(monthly, first(monthly, "booking_month_start", "booking_month"), first(monthly, "total_bookings", "total_booking_records"), "Monthly bookings")
with b:
    line(daily, first(daily, "booking_date", "booking_day"), first(daily, "total_bookings", "total_booking_records"), "Daily bookings")
monthly_count = first(monthly, "total_bookings", "total_booking_records")
if monthly_count and not monthly.empty:
    peak = top(monthly, monthly_count, 1).iloc[0]
    insight("Peak demand month", f"Highest monthly demand: {peak.get(first(monthly, 'booking_month_start', 'booking_month'), 'N/A')} with {float(peak[monthly_count]):,.0f} booking records.")
section("Data governance and quality")
quality = frame("quality", batch)
if not quality.empty:
    st.dataframe(quality, width='stretch', hide_index=True)
else:
    st.info("Quality summary unavailable for this batch.")
with st.expander("Definitions / interpretive cautions"):
    st.write("Source records are not unique rides. Booking IDs repeat. Completed booking value has no verified currency and is not recognized revenue. No verified timezone is available. Rates are record-based.")
table(monthly, f"overview_monthly_{batch}.csv", "Monthly detailed export")
