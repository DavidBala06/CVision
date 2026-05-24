"""
Pool Maintenance — Module 2 (talent pool freshness).

CSV is the only source of truth in this build (no Obsidian vault). The
"bulk refresh" therefore covers two practical needs:

  1. Stale detection — flag candidates whose last_updated_at is older than
     a threshold so HR knows what to review.
  2. Self-refresh — re-normalize the existing CSV row (dedup + sort
     technologies, lowercase, canonicalize seniority) and bump
     last_updated_at. This is honest about what we *can* do without a live
     external feed.
  3. Manual merge — Module 2c: HR pastes fresh CV / LinkedIn text into a
     form, the LLM extracts fields, and `intelligent_merge` reconciles
     them with the existing row.

A real "auto-pull from LinkedIn" would require either the official LinkedIn
API (paid + GDPR contract) or scraping (against TOS). Neither is implemented
on purpose — see README.
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ai.guardrails import get_system_guardrail_prompt, validate_json_output
from ai.llm_provider import get_chat_llm

load_dotenv()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))

# Canonical seniority labels. The CSV uses a mix of "senior", "mid_to_senior",
# "mid", "junior", "intern" — we keep them as-is on read but normalize
# *during* refresh so HR-typed values stay aligned with what the UI filters on.
_SENIORITY_CANON = {
    "intern": "intern",
    "junior": "junior",
    "mid": "mid",
    "middle": "mid",
    "mid_to_senior": "mid_to_senior",
    "midsenior": "mid_to_senior",
    "senior": "senior",
    "lead": "lead",
    "principal": "lead",
    "staff": "lead",
}


def get_llm():
    return get_chat_llm(temperature=0.01, max_tokens=2048)


def get_stale_candidates(months_threshold: int = 3) -> list[dict]:
    """Identify candidates needing refresh (last_updated > threshold)."""
    if not CSV_PATH.exists():
        return []

    stale = []
    cutoff = datetime.now() - timedelta(days=months_threshold * 30)

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            last_updated = row.get("last_updated_at", "")
            if not last_updated:
                stale.append({**row, "days_since_update": "never", "needs_refresh": True})
                continue
            try:
                update_date = datetime.strptime(last_updated.strip(), "%Y-%m-%d")
                days_old = (datetime.now() - update_date).days
                if update_date < cutoff:
                    stale.append({**row, "days_since_update": days_old, "needs_refresh": True})
            except ValueError:
                stale.append({**row, "days_since_update": "invalid_date", "needs_refresh": True})

    return stale


def intelligent_merge(existing_data: dict, new_data: dict) -> dict:
    """AI-powered merge of an existing CSV row with newly-pulled data."""
    llm = get_llm()
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are an HR data merge specialist. Compare two candidate profiles and produce a merged version.

MERGE RULES:
1. New field has data, old empty → use new.
2. Both have data → prefer new (more recent).
3. Old has data, new empty → KEEP old.
4. For 'technologies', merge both lists (union, deduplicated, lowercase).
5. For 'previous_jobs', combine without duplicating.
6. For 'years_of_experience', use the higher value.

Return merged JSON with keys: name, seniority, years_of_experience, current_role,
previous_jobs, degrees, location, languages, technologies, project_summary,
linkedin_url, github_url, email.
{format_instructions}
"""),
        ("human", "EXISTING:\n{existing}\n\nNEW DATA:\n{new_data}\n\nMerge these profiles.")
    ])

    chain = prompt | llm | parser
    try:
        result = chain.invoke({
            "existing": str(existing_data),
            "new_data": str(new_data),
            "format_instructions": parser.get_format_instructions()
        })
        validated, ok = validate_json_output(result)
        if not ok or not isinstance(validated, dict):
            raise ValueError("LLM returned invalid merge")
        return validated
    except Exception as e:
        logger.warning("Merge fell back to deterministic merge: %s", e)
        merged = dict(existing_data)
        for key, value in new_data.items():
            if value and key in merged:
                merged[key] = value
        return merged


# ---------------------------------------------------------------------------
# CSV-only self-refresh — see module docstring.
# ---------------------------------------------------------------------------

def _normalize_tech(raw: str) -> str:
    """Lowercase, dedup, sort the comma-separated technologies field."""
    if not raw:
        return ""
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return ", ".join(sorted(set(parts)))


def _normalize_seniority(raw: str) -> str:
    """Map common variants to the canonical label set."""
    if not raw:
        return raw
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    return _SENIORITY_CANON.get(key, raw.strip().lower())


def _self_refresh_row(row: dict) -> tuple[dict, list[str]]:
    """Return (new_row, list_of_changed_fields) — no external lookups."""
    changes = []
    new_row = dict(row)

    new_tech = _normalize_tech(row.get("technologies", ""))
    if new_tech and new_tech != row.get("technologies", ""):
        new_row["technologies"] = new_tech
        changes.append("technologies")

    new_sen = _normalize_seniority(row.get("seniority", ""))
    if new_sen and new_sen != row.get("seniority", ""):
        new_row["seniority"] = new_sen
        changes.append("seniority")

    return new_row, changes


def bulk_refresh_candidates(candidate_names: list[str]) -> dict:
    """Refresh the listed candidates against the local CSV (no external sources).

    For each selected row we:
      • normalize the `technologies` field (dedup, sort, lowercase)
      • normalize `seniority` to the canonical label
      • bump `last_updated_at` to today

    Real LinkedIn re-pulling is out of scope (no API integration); use the
    /api/refresh/merge endpoint to manually feed new data into the merge flow.
    """
    if not CSV_PATH.exists():
        return {"error": "CSV not found", "refreshed_count": 0}

    rows: list[dict] = []
    refreshed_with_changes: list[dict] = []
    timestamp_only: list[str] = []
    target_set = {n.strip().lower() for n in candidate_names}

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("name", "").strip().lower() in target_set:
                new_row, changes = _self_refresh_row(row)
                if changes:
                    refreshed_with_changes.append({"name": new_row["name"], "changed_fields": changes})
                else:
                    timestamp_only.append(new_row["name"])
                new_row["last_updated_at"] = datetime.now().strftime("%Y-%m-%d")
                row = new_row
            rows.append(row)

    if refreshed_with_changes or timestamp_only:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return {
        "refreshed_count": len(refreshed_with_changes) + len(timestamp_only),
        "normalized": refreshed_with_changes,
        "timestamp_only": timestamp_only,
        "note": (
            "CSV-only self-refresh: technologies & seniority normalized, "
            "last_updated_at bumped. For new external data, use /api/refresh/merge."
        ),
        "total_in_pool": len(rows),
    }


def get_pool_stats() -> dict:
    """Talent pool statistics for the metrics dashboard."""
    if not CSV_PATH.exists():
        return {"total": 0}

    total = active = pending = stale_count = 0
    cutoff = datetime.now() - timedelta(days=180)
    seniority_dist: dict = {}
    location_dist: dict = {}

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            status = row.get("status", "")
            if status == "active":
                active += 1
            elif status == "pending_consent":
                pending += 1

            last_updated = row.get("last_updated_at", "")
            try:
                if last_updated and datetime.strptime(last_updated.strip(), "%Y-%m-%d") < cutoff:
                    stale_count += 1
            except ValueError:
                pass

            sen = row.get("seniority", "unknown") or "unknown"
            seniority_dist[sen] = seniority_dist.get(sen, 0) + 1
            loc = row.get("location", "unknown") or "unknown"
            location_dist[loc] = location_dist.get(loc, 0) + 1

    return {
        "total": total, "active": active, "pending_consent": pending,
        "stale": stale_count, "seniority_distribution": seniority_dist,
        "location_distribution": location_dist,
    }
