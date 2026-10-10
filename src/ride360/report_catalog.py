"""Local, allowlisted report discovery for the RIDE360 Report Center."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPORT_FOLDERS = ("powerbi", "pdfs", "excel", "exports")
EXTENSIONS = {".pbix", ".pdf", ".xlsx", ".xls", ".csv", ".png", ".pptx"}
MIME_TYPES = {
    ".pbix": "application/octet-stream",
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".png": "image/png",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
MAX_DOWNLOAD_BYTES = 150 * 1024 * 1024


@dataclass(frozen=True)
class Report:
    name: str
    category: str
    path: Path
    size_bytes: int
    modified_at: float

    @property
    def extension(self) -> str:
        return self.path.suffix.lower()


def discover_reports(root: Path) -> list[Report]:
    """Find supported regular files only under the explicit report directories."""
    root = root.resolve()
    found: list[Report] = []
    for folder in REPORT_FOLDERS:
        directory = root / folder
        if not directory.is_dir() or directory.is_symlink():
            continue
        for path in directory.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            if path.suffix.lower() not in EXTENSIONS:
                continue
            resolved = path.resolve()
            if not resolved.is_relative_to(directory.resolve()):
                continue
            stat = resolved.stat()
            found.append(Report(
                name=resolved.stem.replace("_", " ").replace("-", " "),
                category=folder.title(),
                path=resolved,
                size_bytes=stat.st_size,
                modified_at=stat.st_mtime,
            ))
    return sorted(found, key=lambda r: r.modified_at, reverse=True)


def read_report(report: Report, root: Path) -> bytes:
    """Revalidate an allowlisted report before downloading it."""
    root = root.resolve()
    resolved = report.path.resolve()
    if report.path.is_symlink() or not any(
        resolved.is_relative_to((root / folder).resolve())
        and (root / folder).is_dir()
        and not (root / folder).is_symlink()
        for folder in REPORT_FOLDERS
    ):
        raise ValueError("Report is outside an approved report directory")
    if resolved.suffix.lower() not in EXTENSIONS or not resolved.is_file():
        raise ValueError("Unsupported report")
    if resolved.stat().st_size > MAX_DOWNLOAD_BYTES:
        raise ValueError("Report exceeds the in-app download size limit")
    return resolved.read_bytes()
