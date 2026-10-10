"""Premium RIDE360 shared UI, resilient analytical helpers and cached queries."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CSS = Path(__file__).resolve().parent / "assets" / "style.css"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ride360.dashboard_data import fetch_batches, fetch_view, to_csv_bytes

COLORS = ["#3BD7E8", "#A78BFA", "#34D399", "#FBBF24", "#FB7185", "#60A5FA"]


@st.cache_data(ttl=900, show_spinner=False)
def batches() -> pd.DataFrame:
    return fetch_batches()


@st.cache_data(ttl=900, show_spinner=False)
def data(name: str, batch_id: int) -> pd.DataFrame:
    return fetch_view(name, batch_id)


def setup_page(title: str, subtitle: str = "") -> int:
    st.set_page_config(page_title=f"{title} Â· RIDE360", page_icon="ðŸš•", layout="wide")
    if CSS.exists():
        # Only a trusted, local stylesheet is passed to st.html; no data-driven HTML.
        st.html(f"<style>{CSS.read_text(encoding='utf-8')}</style>")
    st.sidebar.title("â—ˆ RIDE360")
    st.sidebar.divider()
    try:
        available = batches()
    except (psycopg.Error, OSError, ValueError, RuntimeError) as exc:
        st.error(f"Could not load warehouse batches: {exc}")
        st.stop()
    if available.empty or "batch_id" not in available:
        st.warning("No analytical batches found.")
        st.stop()
    batch = st.sidebar.selectbox("Ingestion batch", [int(x) for x in available["batch_id"]], key="batch")
    if st.sidebar.button("â†» Refresh warehouse cache", width='stretch'):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.divider()
    st.sidebar.caption("SOURCE-RECORD ANALYTICS")
    st.sidebar.caption("No verified currency or timezone")
    st.sidebar.caption("Booking IDs are not unique")
    st.title(title)
    return int(batch)


def frame(name: str, batch: int) -> pd.DataFrame:
    try:
        with st.spinner(f"Loading {name} analyticsâ€¦"):
            return data(name, batch)
    except (psycopg.Error, OSError, ValueError, RuntimeError) as exc:
        st.error(f"Unable to load {name}: {exc}")
        st.stop()


def first(df: pd.DataFrame, *names: str) -> str | None:
    return next((name for name in names if name in df.columns), None)


def val(df: pd.DataFrame, *names: str, default: float = 0) -> float:
    key = first(df, *names)
    if not key or df.empty:
        return default
    series = pd.to_numeric(df[key], errors="coerce")
    return float(series.sum()) if series.notna().any() else default


def cell(df: pd.DataFrame, *names: str, default: object = "N/A") -> object:
    key = first(df, *names)
    return df.iloc[0][key] if key and not df.empty else default


def rate(part: float, whole: float) -> float:
    return 100 * part / whole if whole else 0.0


def metric(label: str, value: object, suffix: str = "", digits: int = 0, help_text: str | None = None) -> None:
    numeric: float | None = None
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        try:
            numeric = float(value)
        except ValueError:
            numeric = None
    shown = f"{numeric:,.{digits}f}{suffix}" if numeric is not None else str(value)
    st.metric(label, shown, help=help_text)


def plot(fig: go.Figure, height: int = 410) -> None:
    fig.update_layout(
        template="plotly_dark", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#d9e7fa"},
        title_font={"size": 17, "color": "#f1f7ff"},
        margin={"l": 10, "r": 10, "t": 55, "b": 20},
        colorway=COLORS, legend_title_text="",
    )
    fig.update_xaxes(gridcolor="#25364e", zeroline=False)
    fig.update_yaxes(gridcolor="#25364e", zeroline=False)
    st.plotly_chart(fig, width='stretch')


def bar(df: pd.DataFrame, x: str | None, y: str | None, title: str, horizontal: bool = False, color: str | None = None) -> None:
    if not x or not y or df.empty or x not in df or y not in df:
        st.info(f"{title}: required fields not available")
        return
    copy = df.copy()
    copy[y] = pd.to_numeric(copy[y], errors="coerce")
    fig = px.bar(copy, x=y if horizontal else x, y=x if horizontal else y,
                 orientation="h" if horizontal else "v", color=color if color in copy else None,
                 title=title, color_discrete_sequence=COLORS)
    if horizontal:
        fig.update_layout(yaxis_categoryorder="total ascending")
    plot(fig)


def line(df: pd.DataFrame, x: str | None, y: str | None, title: str, color: str | None = None) -> None:
    if not x or not y or df.empty or x not in df or y not in df:
        st.info(f"{title}: required fields not available")
        return
    copy = df.copy()
    copy[y] = pd.to_numeric(copy[y], errors="coerce")
    fig = px.line(copy.sort_values(x), x=x, y=y, color=color if color in copy else None,
                  markers=True, title=title, color_discrete_sequence=COLORS)
    plot(fig)


def donut(df: pd.DataFrame, names: str, values: str, title: str) -> None:
    if df.empty or names not in df or values not in df:
        st.info(f"{title}: no data")
        return
    fig = px.pie(df, names=names, values=values, hole=.67, title=title,
                 color_discrete_sequence=COLORS)
    fig.update_traces(textinfo="percent+label", textposition="outside")
    plot(fig)


def top(df: pd.DataFrame, column: str | None, n: int = 12) -> pd.DataFrame:
    if not column or column not in df:
        return df.head(0)
    return df.assign(**{column: pd.to_numeric(df[column], errors="coerce")}).nlargest(n, column)


def table(df: pd.DataFrame, filename: str, title: str = "") -> None:
    if title:
        st.subheader(title)
    if df.empty:
        st.info("No data available for this selection.")
        return
    st.dataframe(df, width='stretch', hide_index=True, height=min(520, 95 + len(df) * 35))
    st.download_button("â†“ Export CSV", to_csv_bytes(df), file_name=filename,
                       mime="text/csv", key=f"csv_{filename}")


def insight(title: str, explanation: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(explanation)


def section(title: str, subtitle: str = "") -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)
