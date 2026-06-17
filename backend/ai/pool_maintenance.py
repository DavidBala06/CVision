"""
Pool Maintenance Module

Handles:
Bulk refresh -- update batch of candidates
Auto-update -- flag candidates with last_updated > 3 months
Manual update -- detect existing candidate, intelligent merge
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ai.guardrails import get_system_guardrail_prompt

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.01,
        max_tokens=2048,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )


def get_stale_candidates(months_threshold: int = 3) -> list[dict]:
    """Identify candidates needing refresh (last_updated > threshold)."""
    from database import get_session, Candidate

    stale = []
    cutoff = datetime.now() - timedelta(days=months_threshold * 30)

    session = get_session()
    try:
        candidates = session.query(Candidate).all()
        for c in candidates:
            last_updated = (c.last_updated_at or "").strip()
            if not last_updated:
                stale.append({**c.to_dict(), "days_since_update": "never", "needs_refresh": True})
                continue
            try:
                update_date = datetime.strptime(last_updated, "%Y-%m-%d")
                days_old = (datetime.now() - update_date).days
                if update_date < cutoff:
                    stale.append({**c.to_dict(), "days_since_update": days_old, "needs_refresh": True})
            except ValueError:
                stale.append({**c.to_dict(), "days_since_update": "invalid_date", "needs_refresh": True})
    finally:
        session.close()

    return stale


def intelligent_merge(existing_data: dict, new_data: dict) -> dict:
    """AI-powered intelligent merge of old and new candidate data."""
    llm = get_llm()
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are an HR data merge specialist. Compare two candidate profiles and produce a merged version.

MERGE RULES:
1. New field has data, old empty -> use new.
2. Both have data -> prefer new (more recent).
3. Old has data, new empty -> KEEP old.
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
    """Mark selected candidates as refreshed (update timestamp)."""
    from database import get_session, Candidate

    session = get_session()
    refreshed = []

    try:
        candidates = session.query(Candidate).filter(
            Candidate.name.in_(candidate_names)
        ).all()

        for candidate in candidates:
            github_url = candidate.github_url or ""
            if github_url:
                from ai.github_sourcing import scrape_github_for_refresh
                new_data = scrape_github_for_refresh(github_url)
                if new_data:
                    print(f"[Maintenance] Merging new GitHub data for {candidate.name}")
                    merged = intelligent_merge(candidate.to_dict(), new_data)
                    for key, value in merged.items():
                        if value and hasattr(candidate, key):
                            setattr(candidate, key, value)

            candidate.last_updated_at = datetime.now().strftime("%Y-%m-%d")
            refreshed.append(candidate.name)

        total = session.query(Candidate).count()
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[Maintenance] Refresh error: {e}")
        total = 0
    finally:
        session.close()

    return {
        "refreshed_count": len(refreshed),
        "refreshed_names": refreshed,
        "total_in_pool": total
    }


def get_pool_stats() -> dict:
    """Get talent pool statistics for metrics dashboard."""
    from database import get_session, Candidate

    session = get_session()
    try:
        candidates = session.query(Candidate).all()
        total = len(candidates)
        active = 0
        pending = 0
        stale_count = 0
        cutoff = datetime.now() - timedelta(days=180)
        seniority_dist = {}
        location_dist = {}

        for c in candidates:
            status = c.status or ""
            if status == "active":
                active += 1
            elif status == "pending_consent":
                pending += 1

            last_updated = (c.last_updated_at or "").strip()
            try:
                if last_updated and datetime.strptime(last_updated, "%Y-%m-%d") < cutoff:
                    stale_count += 1
            except ValueError:
                pass

            sen = c.seniority or "unknown"
            seniority_dist[sen] = seniority_dist.get(sen, 0) + 1
            loc = c.location or "unknown"

            # Normalize location
            loc_lower = loc.lower()
            if not loc_lower or loc_lower == "unknown" or loc_lower == "romania":
                loc = "Romania"
            elif "cluj" in loc_lower:
                loc = "Cluj-Napoca"
            elif "bucharest" in loc_lower or "bucuresti" in loc_lower:
                if "timisoara" in loc_lower:
                    loc = "Bucharest / Timisoara"
                else:
                    loc = "Bucharest"
            else:
                loc = loc.replace(", Romania", "").replace(", Romania", "").strip()

            location_dist[loc] = location_dist.get(loc, 0) + 1

        return {
            "total": total, "active": active, "pending_consent": pending,
            "stale": stale_count, "seniority_distribution": seniority_dist,
            "location_distribution": location_dist,
        }
    finally:
        session.close()
