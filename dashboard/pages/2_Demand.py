"""Temporal demand intelligence."""
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (
    bar,
    first,
    frame,
    insight,
    line,
    metric,
    plot,
    section,
    setup_page,
    table,
    top,
    val,
)

batch = setup_page("Demand Signals", "SEASONALITY  /  PEAK HOURS  /  WEEKDAY × HOUR")
daily = frame("daily", batch)
monthly = frame("monthly", batch)
hourly = frame("hourly", batch)
weekday = frame("weekday", batch)
col_month = first(monthly, "total_bookings", "total_booking_records")
col_hour = first(hourly, "total_bookings", "total_booking_records")
col_day = first(daily, "total_bookings", "total_booking_records")
peak_h = top(hourly, col_hour, 1)
peak_m = top(monthly, col_month, 1)
a, b, c, d = st.columns(4)
with a:
    metric("Booking records", val(monthly, "total_bookings", "total_booking_records"))
with b:
    metric("Active booking dates", len(daily))
with c:
    metric("Peak hour", f"{int(peak_h.iloc[0].get('booking_hour', 0)):02d}:00" if not peak_h.empty else "N/A")
with d:
    metric("Peak month records", peak_m.iloc[0][col_month] if not peak_m.empty and col_month else "N/A")
st.divider()
period = st.radio("Demand timeline", ["Daily", "Monthly"], horizontal=True)
if period == "Daily":
    line(daily, first(daily, "booking_date", "booking_day"), col_day, "Daily booking volume")
else:
    line(monthly, first(monthly, "booking_month_start", "booking_month"), col_month, "Monthly booking volume")
a, b = st.columns(2)
with a:
    bar(hourly, first(hourly, "booking_hour"), col_hour, "Hour-of-day demand")
with b:
    bar(weekday, first(weekday, "booking_iso_weekday", "weekday_name", "booking_weekday_name"), first(weekday, "total_bookings", "total_booking_records"), "Weekday demand")
section("Demand heatmap", "Hourly intensity across the seven weekdays")
heatmap = frame("heatmap", batch)
wd = first(heatmap, "booking_iso_weekday", "weekday_number")
hr = first(heatmap, "booking_hour")
volume = first(heatmap, "total_bookings", "total_booking_records")
if wd and hr and volume and not heatmap.empty:
    matrix = heatmap.pivot_table(index=wd, columns=hr, values=volume, aggfunc="sum", fill_value=0)
    fig = px.imshow(matrix, aspect="auto", color_continuous_scale=[[0, "#14243d"], [.5, "#246aa3"], [1, "#3bd7e8"]], title="Weekday × hour booking intensity")
    plot(fig, 450)
else:
    st.info("Heatmap field mapping unavailable; raw data remains exportable.")
section("Daypart demand")
daypart = frame("daypart", batch)
bar(daypart, first(daypart, "booking_daypart", "daypart"), first(daypart, "total_bookings", "total_booking_records"), "Demand by daypart")
a, b = st.columns(2)
with a:
    table(top(hourly, col_hour, 10), f"peak_hours_{batch}.csv", "Top booking hours")
with b:
    table(top(daily, col_day, 10), f"peak_days_{batch}.csv", "Top booking dates")
if not peak_h.empty and col_hour:
    insight("Operational planning signal", f"Hour {peak_h.iloc[0].get('booking_hour', 'N/A')} had {float(peak_h.iloc[0][col_hour]):,.0f} bookings. Compare with service-risk rates before considering supply adjustments.")
with st.expander("Methodology"):
    st.write("Source timestamps are treated as recorded; timezone is unverified. Demand counts are booking records, not verified unique journeys.")
