"""
Pure-Python CSV operations on the talent pool.

Kept separate from cv_ingestion.py so the dedup/write logic can be tested
without pulling in LangChain. Anything LLM-driven lives in cv_ingestion.py
and depends on these helpers.
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))

CSV_FIELDNAMES = [
    "name", "seniority", "years_of_experience", "current_role",
    "previous_jobs", "degrees", "location", "languages",
    "technologies", "project_summary", "linkedin_url", "github_url",
    "email", "status", "outreach_status", "outreach_date", "last_updated_at",
]


def _csv_path() -> Path:
    """Re-resolve at call time so tests that monkeypatch CSV_PATH (via env) work."""
    return Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))


def check_duplicate(name: str, email: str = "", linkedin_url: str = "") -> dict | None:
    """Return the existing row if a candidate already exists in the pool."""
    path = _csv_path()
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if name and row.get("name", "").strip().lower() == name.strip().lower():
                return row
            if email and row.get("email", "").strip().lower() == email.strip().lower():
                return row
            if linkedin_url and row.get("linkedin_url", "").strip().lower() == linkedin_url.strip().lower():
                return row
    return None


def add_candidate_to_csv(candidate_data: dict) -> bool:
    """Append a new row to the CSV, filling defaults for missing fields."""
    path = _csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    candidate_data.setdefault("status", "active")
    candidate_data.setdefault("outreach_status", "not_contacted")
    candidate_data.setdefault("outreach_date", "")
    candidate_data.setdefault("last_updated_at", datetime.now().strftime("%Y-%m-%d"))
    candidate_data.setdefault("github_url", "")

    file_exists = path.exists()
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            row = {k: candidate_data.get(k, "") for k in CSV_FIELDNAMES}
            writer.writerow(row)
        return True
    except Exception as e:
        logger.exception("Error writing to CSV: %s", e)
        return False


def update_candidate_in_csv(name: str, updated_data: dict) -> bool:
    """Update an existing candidate's row. Only non-empty new values overwrite."""
    path = _csv_path()
    if not path.exists():
        return False

    rows = []
    updated = False

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("name", "").strip().lower() == name.strip().lower():
                for key, value in updated_data.items():
                    if value and key in row:
                        row[key] = value
                row["last_updated_at"] = datetime.now().strftime("%Y-%m-%d")
                updated = True
            rows.append(row)

    if updated:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return updated
