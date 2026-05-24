"""Tests for the duplicate detection in csv_store (no LLM dependencies)."""
import csv
from pathlib import Path


def _make_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "talent_pool.csv"
    rows = [
        {
            "name": "Alice Anderson", "seniority": "senior", "years_of_experience": "8",
            "current_role": "Backend Engineer", "previous_jobs": "",
            "degrees": "", "location": "Berlin", "languages": "en",
            "technologies": "python", "project_summary": "",
            "linkedin_url": "https://linkedin.com/in/alice",
            "github_url": "", "email": "alice@example.com",
            "status": "active", "outreach_status": "not_contacted",
            "outreach_date": "", "last_updated_at": "2026-01-01",
        }
    ]
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def test_dedup_by_name(tmp_path, monkeypatch):
    csv_path = _make_csv(tmp_path)
    monkeypatch.setenv("CSV_PATH", str(csv_path))

    from ai.csv_store import check_duplicate
    found = check_duplicate(name="alice anderson")
    assert found is not None
    assert found["email"] == "alice@example.com"


def test_dedup_by_email(tmp_path, monkeypatch):
    csv_path = _make_csv(tmp_path)
    monkeypatch.setenv("CSV_PATH", str(csv_path))

    from ai.csv_store import check_duplicate
    found = check_duplicate(name="Bob", email="alice@example.com")
    assert found is not None
    assert found["name"] == "Alice Anderson"


def test_dedup_by_linkedin(tmp_path, monkeypatch):
    csv_path = _make_csv(tmp_path)
    monkeypatch.setenv("CSV_PATH", str(csv_path))

    from ai.csv_store import check_duplicate
    found = check_duplicate(name="Different Name", linkedin_url="https://linkedin.com/in/alice")
    assert found is not None


def test_no_match_returns_none(tmp_path, monkeypatch):
    csv_path = _make_csv(tmp_path)
    monkeypatch.setenv("CSV_PATH", str(csv_path))

    from ai.csv_store import check_duplicate
    found = check_duplicate(name="Nobody Here")
    assert found is None


def test_add_and_update_roundtrip(tmp_path, monkeypatch):
    csv_path = _make_csv(tmp_path)
    monkeypatch.setenv("CSV_PATH", str(csv_path))

    from ai.csv_store import add_candidate_to_csv, check_duplicate, update_candidate_in_csv

    assert add_candidate_to_csv({
        "name": "Bob Builder",
        "seniority": "mid",
        "email": "bob@example.com",
        "technologies": "go",
    })
    found = check_duplicate(name="Bob Builder")
    assert found is not None
    assert found["technologies"] == "go"

    assert update_candidate_in_csv("Bob Builder", {"technologies": "go, rust"})
    refreshed = check_duplicate(name="Bob Builder")
    assert refreshed["technologies"] == "go, rust"
