"""
Pool Maintenance Module 

Handles:
Bulk refresh — update batch of candidates
Auto-update — flag candidates with last_updated > 3 months
Manual update — detect existing candidate, intelligent merge
"""
import os
import csv
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ai.guardrails import get_system_guardrail_prompt

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))


def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.01,
        max_tokens=2048,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )


def get_stale_candidates(months_threshold: int = 3) -> list[dict]:
    #Identify candidates needing refresh (last_updated > threshold)
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
    # AI-powered intelligent merge of old and new candidate data.
    llm = get_llm()
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are an HR data merge specialist. Compare two candidate profiles and produce a merged version.

MERGE RULES:
1. New field has data, old empty → use new.
2. Both have data → prefer new (more recent).
3. Old has data, new empty → KEEP old.
4. For 'technologies', merge both lists (union).
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
        return result if isinstance(result, dict) else existing_data
    except Exception as e:
        print(f"Merge error: {e}")
        merged = dict(existing_data)
        for key, value in new_data.items():
            if value and key in merged:
                merged[key] = value
        return merged


def bulk_refresh_candidates(candidate_names: list[str]) -> dict:
    # Mark selected candidates as refreshed (update timestamp).
    if not CSV_PATH.exists():
        return {"error": "CSV not found", "refreshed": 0}

    rows = []
    refreshed = []

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("name", "").strip() in candidate_names:
                row["last_updated_at"] = datetime.now().strftime("%Y-%m-%d")
                refreshed.append(row["name"])
            rows.append(row)

    if refreshed:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return {
        "refreshed_count": len(refreshed),
        "refreshed_names": refreshed,
        "total_in_pool": len(rows)
    }


def get_pool_stats() -> dict:
    #Get talent pool statistics for metrics dashboard.
    if not CSV_PATH.exists():
        return {"total": 0}

    total = active = pending = stale_count = 0
    cutoff = datetime.now() - timedelta(days=180)
    seniority_dist = {}
    location_dist = {}

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
