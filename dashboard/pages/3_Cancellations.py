"""Cancellation and service reliability intelligence."""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
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
    plot,
    rate,
    section,
    setup_page,
    table,
    top,
    val,
)

batch = setup_page("Service Reliability", "CANCELLATION OWNERSHIP  /  ROOT-CAUSE SIGNALS  /  SERVICE RISK")
monthly = frame("cancellations", batch)
reasons = frame("cancellation_reasons", batch)
customer = val(monthly, "customer_cancellations", "cancelled_by_customer")
driver = val(monthly, "driver_cancellations", "cancelled_by_driver")
cancelled = val(monthly, "total_cancellations", "cancelled_bookings") or customer + driver
bookings = val(monthly, "total_bookings", "total_booking_records")
a, b, c, d = st.columns(4)
with a:
    metric("Total cancellations", cancelled)
with b:
    metric("Customer cancellations", customer)
with c:
    metric("Driver cancellations", driver)
with d:
    metric("Cancellation rate", rate(cancelled, bookings), "%", 2)
a, b = st.columns(2)
actors = pd.DataFrame({"Actor": ["Customer", "Driver"], "Records": [customer, driver]})
with a:
    donut(actors, "Actor", "Records", "Cancellation ownership")
with b:
    bar(actors, "Actor", "Records", "Customer vs driver cancellations")
insight("Where to investigate", f"Driver cancellations account for {rate(driver, cancelled):.1f}% of cancellations; customer cancellations account for {rate(customer, cancelled):.1f}%. These are recorded outcomes, not proven root causes.")
section("Monthly reliability trajectory")
date = first(monthly, "booking_month_start", "booking_month")
if date and "customer_cancellations" in monthly and "driver_cancellations" in monthly:
    fig = px.bar(monthly.sort_values(date), x=date, y=["customer_cancellations", "driver_cancellations"], barmode="group", title="Cancellation ownership by month", color_discrete_sequence=["#3bd7e8", "#fb7185"])
    plot(fig)
else:
    line(monthly, date, first(monthly, "total_cancellations", "cancelled_bookings"), "Monthly cancellation volume")
section("Cancellation reason explorer")
actor = first(reasons, "cancellation_actor", "cancellation_type", "actor")
reason = first(reasons, "cancellation_reason", "reason", "reason_text")
count = first(reasons, "cancellation_records", "total_cancellations", "reason_count", "booking_records")
if actor and reason and count and not reasons.empty:
    choices = sorted(reasons[actor].dropna().astype(str).unique())
    selected = st.selectbox("Cancellation category", ["All", *choices])
    filtered = reasons if selected == "All" else reasons[reasons[actor].astype(str) == selected]
    grouped = filtered.groupby(reason, dropna=False)[[count]].sum().reset_index()
    grouped[reason] = grouped[reason].fillna("Unspecified")
    grouped = grouped[[reason, count]].copy()
    bar(top(grouped, count, 15), reason, count, "Most frequently recorded cancellation reasons", horizontal=True)
    table(grouped, f"cancellation_reasons_{batch}.csv", "Reason-level breakdown")
else:
    st.info("Reason breakdown requires actor, reason and count fields. Inspect the underlying view below.")
    table(reasons, f"cancellation_reasons_raw_{batch}.csv")
section("Hourly service availability")
risk = frame("hourly_risk", batch)
hour = first(risk, "booking_hour")
risk_col = first(risk, "no_driver_found_rate_pct", "no_driver_found_pct")
line(risk, hour, risk_col, "No-driver-found rate by booking hour (%)")
if risk_col:
    table(top(risk, risk_col, 8), f"hourly_risk_{batch}.csv", "Highest-risk booking hours")
with st.expander("Definitions and caveats"):
    st.write("No Driver Found is distinct from customer/driver cancellations. Source cancellation reasons are descriptive labels, not causal proof. Compare rate and volume before prioritizing operational interventions.")
