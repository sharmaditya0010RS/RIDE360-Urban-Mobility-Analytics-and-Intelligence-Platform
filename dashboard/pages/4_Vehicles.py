"""Vehicle category performance intelligence."""
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
    line,
    metric,
    rate,
    section,
    setup_page,
    table,
)

batch = setup_page("Fleet Intelligence", "CATEGORY MIX  /  COMPLETION EFFICIENCY  /  BOOKING VALUE")
raw = frame("vehicles", batch)
vehicle = first(raw, "vehicle_type", "vehicle_category")
volume = first(raw, "total_bookings", "total_booking_records")
completed = first(raw, "completed_bookings")
value = first(raw, "completed_booking_value_total", "completed_booking_value")
if not vehicle or not volume or raw.empty:
    st.warning("Vehicle category and booking count fields are required.")
    st.stop()
raw = raw.copy()
measures = [name for name in [volume, completed, value] if name]
for name in measures:
    raw[name] = pd.to_numeric(raw[name], errors="coerce").fillna(0)
summary = raw.groupby(vehicle, dropna=False, as_index=False)[measures].sum()
summary["booking_share_pct"] = summary[volume] / max(float(summary[volume].sum()), 1) * 100
if completed:
    summary["completion_rate_pct"] = summary.apply(lambda r: rate(r[completed], r[volume]), axis=1)
summary = summary.sort_values(volume, ascending=False)
leader = summary.iloc[0]
a, b, c, d = st.columns(4)
with a:
    metric("Vehicle categories", len(summary))
with b:
    metric("Category-linked bookings", summary[volume].sum())
with c:
    metric("Leading category", leader[vehicle])
with d:
    metric("Leader demand share", leader["booking_share_pct"], "%", 2)
st.divider()
a, b = st.columns(2)
with a:
    bar(summary, vehicle, volume, "Booking volume by category", horizontal=True)
with b:
    donut(summary, vehicle, volume, "Category share")
section("Performance comparison")
metrics = [volume, "booking_share_pct"] + ([completed, "completion_rate_pct"] if completed else []) + ([value] if value else [])
selected = st.selectbox("Rank vehicle categories by", metrics, format_func=lambda x: x.replace("_", " ").title())
bar(summary.sort_values(selected, ascending=False), vehicle, selected, "Vehicle category leaderboard", horizontal=True)
month = first(raw, "booking_month_start", "booking_month")
section("Vehicle trends over time")
line(raw, month, volume, "Monthly demand by vehicle category", color=vehicle)
if completed:
    best_index = int(summary["completion_rate_pct"].argmax())
    best = summary.iloc[best_index]
    insight("Fulfillment leader", f"{best[vehicle]} has the highest observed completion rate ({best['completion_rate_pct']:.1f}%). Compare its booking volume before interpreting the difference.")
if value:
    insight("Booking-value context", "Completed booking value is a source field with unverified currency and recognition. It is not labeled revenue.")
table(summary.round(2), f"vehicle_scorecard_{batch}.csv", "Vehicle category scorecard")
with st.expander("Methodology"):
    st.write("Vehicle rates are calculated from summed counts, not averaged monthly percentages. Category comparisons do not control for geography, trip type or demand mix.")
