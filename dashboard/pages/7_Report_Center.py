
"""RIDE360 enterprise report and document center."""

from __future__ import annotations

import io
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DASHBOARD_ROOT.parent

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from common import setup_page

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

REPORTS_ROOT = PROJECT_ROOT / "reports"
DOCS_ROOT = PROJECT_ROOT / "docs"
POWERBI_ROOT = REPORTS_ROOT / "powerbi"

SUPPORTED_EXTENSIONS = {
    ".csv",
    ".pdf",
    ".pbix",
    ".pbit",
    ".xlsx",
    ".xls",
    ".md",
    ".txt",
    ".docx",
    ".doc",
    ".rtf",
    ".json",
}

DOCUMENT_EXTENSIONS = {
    ".md",
    ".txt",
    ".docx",
    ".doc",
    ".rtf",
}

EXCLUDED_FILES = {
    "project_inventory.json",
}

DOCUMENT_NAMES = {
    "Analytics Engineering.md",
    "data_contracts.md",
    "Interactive_Analytics_dashboard.md",
    "phase5_start.md",
    "warehouse_architecture.md",
}

CATEGORY_LABELS = {
    "Power BI": "Power BI Dashboards",
    "Business Rules": "Business Rules & Events",
    "Data Dictionary": "Metadata & KPI Contracts",
    "Profiling": "Data Profiling",
    "Data Quality": "Data Quality & Validation",
    "Documentation": "Project Documentation",
    "PDF": "PDF Reports",
    "Excel": "Excel Workbooks",
    "Exports": "Other Exports",
    "Archive": "Historical / Archive",
}


# ---------------------------------------------------------
# FILE DISCOVERY
# ---------------------------------------------------------

def category_for(path: Path) -> str:
    """Assign a business-facing category based on file location."""
    relative = path.relative_to(PROJECT_ROOT)
    parts = [part.lower() for part in relative.parts]
    name = path.name.lower()

    if path.suffix.lower() in {".pbix", ".pbit"}:
        return "Power BI"

    if "docs" in parts:
        return "Documentation"

    if "phase1_final" in parts:
        if "business" in parts:
            return "Business Rules"
        if "events" in parts:
            return "Business Rules"
        if "metadata" in parts:
            return "Data Dictionary"
        if "profiling" in parts:
            return "Profiling"
        if "structural" in parts:
            return "Data Quality"

    if "generated" in parts:
        return "Archive"

    if path.suffix.lower() == ".pdf":
        return "PDF"

    if path.suffix.lower() in {".xlsx", ".xls"}:
        return "Excel"

    if "business" in name or "event" in name:
        return "Business Rules"

    if "dictionary" in name or "kpi" in name:
        return "Data Dictionary"

    return "Exports"


def phase_for(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT).as_posix().lower()

    if "phase1" in relative or "phase_1" in relative:
        return "Phase 1"

    if "phase2" in relative or "warehouse" in relative:
        return "Phase 2"

    if "phase3" in relative:
        return "Phase 3"

    if "phase4" in relative or "dashboard" in relative:
        return "Phase 4"

    if "phase5" in relative:
        return "Phase 5"

    return "General"


def collect_files() -> list[dict]:
    """Collect report assets and curated project documents."""
    results = []
    seen = set()

    scan_roots = [REPORTS_ROOT, DOCS_ROOT]

    for scan_root in scan_roots:
        if not scan_root.is_dir():
            continue

        for path in scan_root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            if path.name in EXCLUDED_FILES:
                continue

            if scan_root == DOCS_ROOT and path.name not in DOCUMENT_NAMES:
                continue

            resolved = path.resolve()

            if resolved in seen:
                continue

            seen.add(resolved)

            stat = path.stat()
            category = category_for(path)

            results.append(
                {
                    "name": path.name,
                    "path": path,
                    "relative_path": path.relative_to(
                        PROJECT_ROOT
                    ).as_posix(),
                    "category": category,
                    "phase": phase_for(path),
                    "format": path.suffix.lower().lstrip(".").upper(),
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                    .strftime("%Y-%m-%d %H:%M"),
                }
            )

    results.sort(
        key=lambda item: (
            item["category"] == "Archive",
            item["category"],
            item["name"].casefold(),
        )
    )

    return results


# ---------------------------------------------------------
# DOWNLOAD AND PREVIEW HELPERS
# ---------------------------------------------------------

def create_zip(files: list[dict]) -> bytes:
    """Create an in-memory ZIP with safe relative paths."""
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for item in files:
            archive.write(
                item["path"],
                arcname=item["relative_path"],
            )

    return buffer.getvalue()


def render_preview(item: dict) -> None:
    """Show a lightweight preview for supported formats."""
    path = item["path"]
    suffix = path.suffix.lower()

    if suffix == ".csv":
        try:
            preview = pd.read_csv(path, nrows=100)
            st.dataframe(
                preview,
                width='stretch',
                hide_index=True,
            )
            st.caption("Preview limited to first 100 rows.")
        except (OSError, UnicodeError, pd.errors.ParserError) as exc:
            st.warning(f"CSV preview unavailable: {exc}")

    elif suffix in {".md", ".txt"}:
        try:
            content = path.read_text(encoding="utf-8")
            st.code(content[:12000], language="markdown")
            if len(content) > 12000:
                st.caption("Preview truncated to 12,000 characters.")
        except (OSError, UnicodeError) as exc:
            st.warning(f"Text preview unavailable: {exc}")

    elif suffix == ".pdf":
        st.info("PDF preview is not enabled. Download to view.")

    elif suffix in {".pbix", ".pbit"}:
        st.info(
            "Power BI files must be opened in Power BI Desktop. "
            "Download the file below."
        )

    else:
        st.info(
            "Preview is not available for this file format. "
            "Use the download button."
        )


# ---------------------------------------------------------
# PAGE
# ---------------------------------------------------------

batch = setup_page(
    "Report & Knowledge Center",
    "Explore generated analytical reports, documentation and Power BI assets.",
)

POWERBI_ROOT.mkdir(parents=True, exist_ok=True)

files = collect_files()

reports = [
    item for item in files
    if item["category"] != "Documentation"
]

documents = [
    item for item in files
    if item["category"] == "Documentation"
]

powerbi = [
    item for item in files
    if item["category"] == "Power BI"
]

archives = [
    item for item in files
    if item["category"] == "Archive"
]

active_reports = [
    item for item in reports
    if item["category"] not in {"Archive", "Power BI"}
]

st.caption(f"Active warehouse batch: {batch}")

a, b, c, d, e = st.columns(5)

a.metric("Curated reports", len(active_reports))
b.metric("Project documents", len(documents))
c.metric("Power BI assets", len(powerbi))
d.metric("Archived reports", len(archives))
e.metric("Total catalog files", len(files))

st.divider()

# ---------------------------------------------------------
# POWER BI DASHBOARD
# ---------------------------------------------------------

st.subheader("Power BI Dashboard")

if not powerbi:
    st.info(
        "RIDE360 Power BI dashboard is coming soon. "
        "The dedicated Power BI report library is ready."
    )

    with st.container(border=True):
        st.markdown("### RIDE360 | Mobility Intelligence Dashboard")
        st.caption("Status: Planned")

        st.write(
            "The upcoming Power BI dashboard will provide "
            "executive KPIs, booking trends, cancellations, "
            "vehicle performance, location intelligence "
            "and customer segmentation."
        )

        st.write(
            "Once the actual `.pbix` file is created, "
            "place it in `reports/powerbi/`. "
            "It will automatically appear here."
        )

else:
    selected_powerbi = st.selectbox(
        "Select Power BI asset",
        powerbi,
        format_func=lambda item: item["name"],
    )

    st.write(f"File: `{selected_powerbi['relative_path']}`")
    st.write(f"Size: {selected_powerbi['size_kb']:,.2f} KB")

    st.download_button(
        "Download Power BI File",
        data=selected_powerbi["path"].read_bytes(),
        file_name=selected_powerbi["name"],
        mime="application/octet-stream",
        width='stretch',
    )

st.divider()

# ---------------------------------------------------------
# REPORT SEARCH AND FILTERS
# ---------------------------------------------------------

st.subheader("Browse Reports & Documents")

search = st.text_input(
    "Search library",
    placeholder="Search KPI contracts, data dictionary, quality reports...",
)

categories = sorted({item["category"] for item in files})
phases = sorted({item["phase"] for item in files})
formats = sorted({item["format"] for item in files})

left, middle, right = st.columns(3)

with left:
    selected_categories = st.multiselect(
        "Category",
        categories,
        default=[],
    )

with middle:
    selected_phases = st.multiselect(
        "Project phase",
        phases,
        default=[],
    )

with right:
    selected_formats = st.multiselect(
        "File format",
        formats,
        default=[],
    )

include_archives = st.toggle(
    "Include historical / archived reports",
    value=False,
)

filtered = []

for item in files:
    if not include_archives and item["category"] == "Archive":
        continue

    if selected_categories and item["category"] not in selected_categories:
        continue

    if selected_phases and item["phase"] not in selected_phases:
        continue

    if selected_formats and item["format"] not in selected_formats:
        continue

    if search:
        searchable = (
            item["name"] + " " + item["relative_path"]
        ).casefold()

        if search.casefold() not in searchable:
            continue

    filtered.append(item)

st.caption(f"Showing {len(filtered)} of {len(files)} catalog files")

if filtered:
    listing = pd.DataFrame(
        [
            {
                "File": item["name"],
                "Category": item["category"],
                "Phase": item["phase"],
                "Format": item["format"],
                "Size (KB)": item["size_kb"],
                "Modified": item["modified"],
                "Path": item["relative_path"],
            }
            for item in filtered
        ]
    )

    st.dataframe(
        listing,
        width='stretch',
        hide_index=True,
        height=420,
    )

    st.download_button(
        "Download Filtered Catalog CSV",
        data=listing.to_csv(index=False).encode("utf-8-sig"),
        file_name="ride360_report_catalog.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download All Filtered Files (ZIP)",
        data=create_zip(filtered),
        file_name="ride360_report_bundle.zip",
        mime="application/zip",
    )

    st.divider()

    st.subheader("Report Preview & Download")

    selected_file = st.selectbox(
        "Select a file",
        filtered,
        index=0,
        format_func=lambda item: (
            f"{item['name']} â€” {item['category']}"
        ) if item is not None else "No file available",
    )

    if selected_file is None:
        st.stop()

    with st.container(border=True):
        st.write(f"**File:** {selected_file['name']}")
        st.write(f"**Category:** {selected_file['category']}")
        st.write(f"**Phase:** {selected_file['phase']}")
        st.write(f"**Path:** `{selected_file['relative_path']}`")
        st.write(f"**Size:** {selected_file['size_kb']:,.2f} KB")
        st.write(f"**Modified:** {selected_file['modified']}")

        st.divider()

        render_preview(selected_file)

        st.download_button(
            "Download Selected File",
            data=selected_file["path"].read_bytes(),
            file_name=selected_file["name"],
            mime="application/octet-stream",
            width='stretch',
        )

else:
    st.warning("No files match the selected filters.")

st.divider()

# ---------------------------------------------------------
# REPORT GOVERNANCE
# ---------------------------------------------------------

with st.expander("Report governance & data interpretation"):
    st.write(
        "Generated CSV reports represent analytical and quality "
        "artifacts, not necessarily presentation-ready business "
        "reports. Archived reports are retained for traceability. "
        "Booking IDs are not unique. Completed booking value is "
        "not verified recognized revenue. Power BI assets are "
        "only downloadable when an actual file exists."
    )
