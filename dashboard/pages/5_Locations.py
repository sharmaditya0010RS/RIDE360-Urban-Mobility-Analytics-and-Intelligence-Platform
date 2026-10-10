"""Pickup hotspots and directional route intelligence."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (
    bar,
    first,
    frame,
    insight,
    metric,
    section,
    setup_page,
    table,
    top,
    val,
)

batch = setup_page("Network Intelligence", "PICKUP HOTSPOTS  /  DIRECTIONAL CORRIDORS  /  LOCATION DRILL-DOWN")
pickups = frame("pickups", batch)
routes = frame("routes", batch)
pickup = first(pickups, "pickup_location", "pickup_point")
count = first(pickups, "total_bookings", "total_booking_records")
origin = first(routes, "pickup_location", "pickup_point")
destination = first(routes, "drop_location", "dropoff_location", "drop_location_name")
route_count = first(routes, "total_bookings", "total_booking_records")
if not pickup or not count or pickups.empty:
    st.warning("Pickup location and booking volume fields are required.")
    st.stop()
leading = top(pickups, count, 1)
a, b, c, d = st.columns(4)
with a:
    metric("Pickup locations", pickups[pickup].nunique())
with b:
    metric("Pickup-linked records", val(pickups, count))
with c:
    metric("Directional corridors", len(routes))
with d:
    metric("Leading pickup", leading.iloc[0][pickup] if not leading.empty else "N/A")
st.divider()
n = st.slider("Top locations / corridors", 5, 30, 15, 5)
section("Pickup concentration")
bar(top(pickups, count, n), pickup, count, "Highest-demand pickup locations", horizontal=True)
with st.expander("Pickup service performance"):
    completion = first(pickups, "completion_rate_pct", "completed_bookings")
    no_driver = first(pickups, "no_driver_found_rate_pct")
    a, b = st.columns(2)
    with a:
        bar(top(pickups, completion, n), pickup, completion, "Pickup completion signal", horizontal=True)
    with b:
        bar(top(pickups, no_driver, n), pickup, no_driver, "No-driver-found risk by pickup", horizontal=True)
section("Directional route leaderboard")
if origin and destination and route_count and not routes.empty:
    routes = routes.copy()
    routes["corridor"] = routes[origin].fillna("Unknown").astype(str) + " → " + routes[destination].fillna("Unknown").astype(str)
    bar(top(routes, route_count, n), "corridor", route_count, "Most frequently booked directional routes", horizontal=True)
    locations = sorted(routes[origin].dropna().astype(str).unique())
    if locations:
        selected = st.selectbox("Explore destinations from pickup", locations)
        selected_routes = routes[routes[origin].astype(str) == selected]
        bar(top(selected_routes, route_count, n), destination, route_count, f"Destinations from {selected}", horizontal=True)
        table(selected_routes, f"origin_routes_{batch}.csv", "Selected origin detail")
else:
    st.info("Route origin/destination columns not found; displaying raw route data.")
    table(routes, f"routes_{batch}.csv")
section("Search pickup locations")
search = st.text_input("Pickup name contains", placeholder="Try Saket, Khandsa or Dwarka")
filtered = pickups[pickups[pickup].astype(str).str.contains(search, case=False, regex=False, na=False)] if search else pickups
table(filtered, f"pickup_network_{batch}.csv", "Pickup performance records")
insight("Network interpretation", "These are source location labels, not verified GPS coordinates. A → B and B → A are distinct directional corridors; counts are booking records.")
