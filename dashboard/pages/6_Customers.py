"""Customer-identifier frequency analytics."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (
    bar,
    donut,
    first,
    frame,
    insight,
    metric,
    rate,
    section,
    setup_page,
    table,
)

batch = setup_page("Customer Signals", "IDENTIFIER FREQUENCY  /  BOOKING CONTRIBUTION  /  SEGMENT PERFORMANCE")
segments = frame("customers", batch)
segment = first(segments, "frequency_segment", "customer_segment")
ids = first(segments, "customer_ids", "customer_count")
bookings = first(segments, "total_booking_records", "total_bookings")
completed = first(segments, "completed_bookings")
if not segment or not ids or not bookings or segments.empty:
    st.warning("Customer segment, identifier count and booking count fields are required.")
    st.stop()
segments = segments.copy()
for col in [ids, bookings, completed]:
    if col:
        segments[col] = pd.to_numeric(segments[col], errors="coerce").fillna(0)
order = first(segments, "segment_sort_order")
if order:
    segments = segments.sort_values(order)
identifier_total = float(segments[ids].sum())
booking_total = float(segments[bookings].sum())
segments["identifier_share_pct"] = segments[ids] / max(identifier_total, 1) * 100
segments["booking_share_pct"] = segments[bookings] / max(booking_total, 1) * 100
# A repeat identifier is one associated with 2+ source booking records.
repeat_mask = segments[segment].astype(str).str.contains(r"2|3|4|5|repeat|frequent|multiple", case=False, regex=True)
repeat_ids = float(segments.loc[repeat_mask, ids].sum())
a, b, c, d = st.columns(4)
with a:
    metric("Distinct customer IDs", identifier_total)
with b:
    metric("Customer-linked records", booking_total)
with c:
    metric("Repeat-segment IDs", repeat_ids)
with d:
    metric("Repeat-segment share", rate(repeat_ids, identifier_total), "%", 2)
st.divider()
a, b = st.columns(2)
with a:
    bar(segments, segment, ids, "Identifiers by frequency segment")
with b:
    donut(segments, segment, ids, "Identifier share by segment")
section("Who contributes the booking records?")
bar(segments, segment, bookings, "Booking records by frequency segment")
if completed:
    segments["completion_rate_pct"] = segments.apply(lambda r: rate(r[completed], r[bookings]), axis=1)
    bar(segments, segment, "completion_rate_pct", "Completion rate by frequency segment (%)")
section("Customer segment scorecard")
table(segments.round(2), f"customer_segments_{batch}.csv", "Segment-level detail")
insight("Interpretation boundary", "Repeat source customer IDs do not prove customer retention, identity verification, loyalty or lifetime value. This dashboard intentionally avoids displaying individual customer identifiers.")
