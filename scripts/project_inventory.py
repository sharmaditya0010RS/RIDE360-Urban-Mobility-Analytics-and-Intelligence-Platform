
"""Scan RIDE360 project documents, reports and Power BI assets."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPORT_EXTENSIONS = {".pdf", ".pbix", ".pbit", ".xlsx", ".xls", ".csv"}
DOCUMENT_EXTENSIONS = {".md", ".docx", ".doc", ".txt", ".rtf"}
DATA_EXTENSIONS = {".csv", ".parquet", ".json", ".xlsx"}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".streamlit",
    "node_modules",
    "premium_patch",
    "dashboard_backup_before_premium",
}

REPORT_ROOT = ROOT / "reports"
OUTPUT_FILE = REPORT_ROOT / "project_inventory.json"


def scan_project() -> dict:
    """Return a categorized inventory of project files."""
    reports = []
    documents = []
    datasets = []
    powerbi = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)

        if any(part in IGNORED_DIRS for part in relative.parts):
            continue

        if path == OUTPUT_FILE:
            continue

        extension = path.suffix.lower()
        location = relative.as_posix()

        record = {
            "name": path.name,
            "path": location,
            "extension": extension,
            "size_kb": round(path.stat().st_size / 1024, 2),
        }

        if extension in DOCUMENT_EXTENSIONS:
            documents.append(record)

        if extension in DATA_EXTENSIONS:
            datasets.append(record)

        if extension in {".pbix", ".pbit"}:
            powerbi.append(record)

        # Reports are files deliberately placed in reports/,
        # not every CSV or Excel file elsewhere in the project.
        if relative.parts[0] == "reports" and (
            extension in REPORT_EXTENSIONS
            or extension in DOCUMENT_EXTENSIONS
        ):
            reports.append(record)

    for collection in (reports, documents, datasets, powerbi):
        collection.sort(key=lambda item: item["path"].casefold())

    report_formats = dict(
        sorted(Counter(item["extension"] for item in reports).items())
    )

    return {
        "project": "RIDE360",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "summary": {
            "total_reports": len(reports),
            "total_documents": len(documents),
            "total_datasets": len(datasets),
            "powerbi_files": len(powerbi),
            "powerbi_dashboard_status": (
                "AVAILABLE" if powerbi else "PLANNED"
            ),
        },
        "report_formats": report_formats,
        "reports": reports,
        "documents": documents,
        "datasets": datasets,
        "powerbi": powerbi,
    }


def main() -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / "powerbi").mkdir(exist_ok=True)
    (REPORT_ROOT / "pdfs").mkdir(exist_ok=True)
    (REPORT_ROOT / "excel").mkdir(exist_ok=True)
    (REPORT_ROOT / "exports").mkdir(exist_ok=True)

    inventory = scan_project()

    OUTPUT_FILE.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = inventory["summary"]

    print("\n" + "=" * 55)
    print("           RIDE360 PROJECT INVENTORY")
    print("=" * 55)
    print(f"Total reports           : {summary['total_reports']}")
    print(f"Total documents         : {summary['total_documents']}")
    print(f"Total datasets          : {summary['total_datasets']}")
    print(f"Power BI files          : {summary['powerbi_files']}")
    print(
        "Power BI dashboard      : "
        f"{summary['powerbi_dashboard_status']}"
    )
    print("=" * 55)

    print("\nREPORTS")
    for item in inventory["reports"]:
        print(f"  - {item['path']}")

    print("\nDOCUMENTS")
    for item in inventory["documents"]:
        print(f"  - {item['path']}")

    print("\nPOWER BI")
    if inventory["powerbi"]:
        for item in inventory["powerbi"]:
            print(f"  - {item['path']}")
    else:
        print("  [PLANNED] Power BI dashboard will be added later.")

    print(f"\nInventory saved: {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
