"""
FastAPI Backend

All API endpoints for the AI Talent Pool Manager.

"""
import io
import os
import csv
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from ai.RAG_engine import build_vector_database, score_shortlist
from ai.cv_ingestion import (
    extract_from_text, check_duplicate, add_candidate_to_pool, update_candidate_in_pool,
    is_github_url, extract_from_github_url,
)
from ai.pool_maintenance import get_stale_candidates, intelligent_merge, bulk_refresh_candidates, get_pool_stats
from ai.outreach_agent import generate_email_draft, generate_followup_draft, update_outreach_status, get_outreach_dashboard
from ai.github_sourcing import search_by_criteria, search_by_profile
from ai.guardrails import sanitize_input
from scraper.parser import extract_text_from_pdf
from auth import init_auth_db, authenticate_user
from database import init_db, get_session, Candidate, HiringRequest, Application

app = FastAPI(title="TalentAI Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

# Initialize Auth DB
print("Initializing Auth Database...")
init_auth_db()

# Initialize main database (candidates, hiring requests, applications)
print("Initializing Main Database...")
init_db()

# Initialize RAG
print("Initializing Vector Database...")
db = build_vector_database()
if db:
    print("Vector database built successfully.")
else:
    print("Warning: Vector database could not be built.")

# Models

class LoginRequest(BaseModel):
    username: str
    password: str

class MatchRequest(BaseModel):
    query: str

class IngestApproveRequest(BaseModel):
    candidate_data: dict
    hiring_request_id: Optional[int] = None

class RefreshRequest(BaseModel):
    candidate_names: list[str]

class EmailDraftRequest(BaseModel):
    candidate_name: str
    job_description: str

class FollowUpRequest(BaseModel):
    candidate_name: str

class OutreachStatusUpdate(BaseModel):
    candidate_name: str
    status: str

class GitHubSearchRequest(BaseModel):
    query: str
    search_type: str  # "criteria" or "profile"

class ManualUpdateRequest(BaseModel):
    candidate_name: str
    new_data: dict

class ExportShortlistRequest(BaseModel):
    candidates: List[dict]
    job_description: str = ""

class AssignToJobRequest(BaseModel):
    candidate_name: str
    source: str = "talent_pool"


# ═══════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════

@app.post("/api/login")
async def login(request: LoginRequest):
    """Authenticate a user against the SQLite users database."""
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {
        "success": True,
        "token": f"session-{user['id']}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "user": {
            "name": user["full_name"],
            "role": user["role"],
            "username": user["username"],
        },
    }


# ═══════════════════════════════════════════
# HIRING REQUESTS
# ═══════════════════════════════════════════

@app.get("/api/hiring-requests")
async def list_hiring_requests():
    """List all hiring requests with aggregated counts."""
    session = get_session()
    try:
        requests = session.query(HiringRequest).all()
        return [hr.to_dict() for hr in requests]
    finally:
        session.close()


@app.get("/api/hiring-requests/{hr_id}")
async def get_hiring_request(hr_id: int):
    """Get a single hiring request with its JD."""
    session = get_session()
    try:
        hr = session.query(HiringRequest).filter(HiringRequest.id == hr_id).first()
        if not hr:
            raise HTTPException(status_code=404, detail="Hiring request not found.")
        return hr.to_dict()
    finally:
        session.close()


@app.get("/api/hiring-requests/{hr_id}/applications")
async def get_applications(hr_id: int):
    """List applications for a hiring request, split into applicants and leads."""
    session = get_session()
    try:
        hr = session.query(HiringRequest).filter(HiringRequest.id == hr_id).first()
        if not hr:
            raise HTTPException(status_code=404, detail="Hiring request not found.")

        apps = session.query(Application).filter(
            Application.hiring_request_id == hr_id
        ).all()

        applicants = [a.to_dict() for a in apps if a.category == "applicant"]
        leads = [a.to_dict() for a in apps if a.category == "lead"]

        return {
            "hiring_request": hr.to_dict(),
            "applicants": applicants,
            "leads": leads,
            "total": len(apps),
        }
    finally:
        session.close()


@app.post("/api/hiring-requests/{hr_id}/assign")
async def assign_to_job(hr_id: int, request: AssignToJobRequest):
    """Assign a candidate from the talent pool to a job opening (creates a lead)."""
    session = get_session()
    try:
        hr = session.query(HiringRequest).filter(HiringRequest.id == hr_id).first()
        if not hr:
            raise HTTPException(status_code=404, detail="Hiring request not found.")

        # Find candidate in DB
        candidate = session.query(Candidate).filter(
            Candidate.name == request.candidate_name
        ).first()

        # Check for existing application
        existing = session.query(Application).filter(
            Application.hiring_request_id == hr_id,
            Application.candidate_name == request.candidate_name,
        ).first()
        if existing:
            return {"success": False, "message": "Candidate already assigned to this job."}

        app_entry = Application(
            hiring_request_id=hr_id,
            candidate_id=candidate.id if candidate else None,
            candidate_name=request.candidate_name,
            source=request.source,
            applied_date=datetime.now().strftime("%Y-%m-%d"),
            step="applied",
            category="lead",
        )
        session.add(app_entry)
        session.commit()

        return {"success": True, "message": f"{request.candidate_name} assigned to {hr.job_title}."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/job-openings")
async def list_job_openings():
    """Lightweight list of open jobs for dropdowns."""
    session = get_session()
    try:
        jobs = session.query(HiringRequest).filter(
            HiringRequest.status == "open"
        ).all()
        return [{"id": j.id, "job_title": j.job_title, "location": j.location, "description": j.description} for j in jobs]
    finally:
        session.close()


# ═══════════════════════════════════════════
# PENDING ACTIONS
# ═══════════════════════════════════════════

@app.get("/api/pending-actions")
async def get_pending_actions():
    """Aggregate actionable tasks for the recruiter dashboard."""
    actions = []

    # 1. Stale profiles
    try:
        stale = get_stale_candidates(months_threshold=3)
        if stale:
            actions.append({
                "type": "stale_profiles",
                "priority": "medium",
                "count": len(stale),
                "candidates": [s["name"] for s in stale[:5]],
                "message": f"{len(stale)} stale profile{'s' if len(stale) != 1 else ''} need a refresh (older than 3 months)",
            })
    except Exception:
        pass

    # 2. Follow-up needed + 3. New applications
    session = get_session()
    try:
        followup_candidates = []
        new_app_candidates = []

        candidates = session.query(Candidate).all()
        for c in candidates:
            if c.outreach_status == "email_sent" and c.outreach_date:
                try:
                    sent_date = datetime.strptime(c.outreach_date.strip(), "%Y-%m-%d")
                    if (datetime.now() - sent_date).days >= 7:
                        followup_candidates.append(c.name)
                except ValueError:
                    pass

            if c.status == "pending_consent":
                new_app_candidates.append(c.name)

        if followup_candidates:
            actions.append({
                "type": "follow_up_needed",
                "priority": "high",
                "count": len(followup_candidates),
                "candidates": followup_candidates[:5],
                "message": f"{len(followup_candidates)} candidate{'s' if len(followup_candidates) != 1 else ''} require follow-up (no response in 7+ days)",
            })

        if new_app_candidates:
            actions.append({
                "type": "new_applications",
                "priority": "high",
                "count": len(new_app_candidates),
                "candidates": new_app_candidates[:5],
                "message": f"Review {len(new_app_candidates)} new candidate{'s' if len(new_app_candidates) != 1 else ''} pending consent",
            })
    finally:
        session.close()

    return {
        "actions": actions,
        "total_actions": sum(a["count"] for a in actions),
    }


# ═══════════════════════════════════════════
# CANDIDATES (from DB)
# ═══════════════════════════════════════════

@app.get("/api/candidates")
async def get_candidates():
    """Return all candidates from database for the dashboard table."""
    session = get_session()
    try:
        candidates = session.query(Candidate).all()
        return [c.to_dict() for c in candidates]
    finally:
        session.close()


@app.get("/api/candidates/by-name/{name}")
async def get_candidate_by_name(name: str):
    """Return full profile for a single candidate, looked up by name."""
    session = get_session()
    try:
        candidate = session.query(Candidate).filter(
            Candidate.name.ilike(name.strip())
        ).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found.")
        return candidate.to_dict()
    finally:
        session.close()


# ═══════════════════════════════════════════
# SHORTLISTING
# ═══════════════════════════════════════════

@app.post("/api/match")
async def match_candidates(request: MatchRequest):
    """Shortlist candidates using the weighted scoring pipeline."""
    clean_query, is_safe = sanitize_input(request.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail="Query contains disallowed patterns.")

    if not db:
        return []

    print(f"\n[API] Match query: {clean_query}")
    try:
        candidates = score_shortlist(clean_query, db, top_n=3)
        print(f"[API] Scorer returned {len(candidates)} ranked candidates")
        return candidates
    except Exception as e:
        print(f"[API] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
# CV INGESTION
# ═══════════════════════════════════════════

@app.post("/api/ingest")
async def ingest_cv(file: UploadFile = File(None), text: str = Form(None)):
    """Upload a CV (PDF) or paste LinkedIn text.
    AI extracts fields -> returns preview for human approval."""
    raw_text = ""

    if file:
        suffix = Path(file.filename).suffix if file.filename else ".pdf"
        tmp_dir = BASE_DIR / "data" / "uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"

        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        raw_text = extract_text_from_pdf(str(tmp_path))

        try:
            os.remove(tmp_path)
        except OSError:
            pass
    elif text:
        raw_text = text
    else:
        raise HTTPException(status_code=400, detail="Provide either a file or text.")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the provided input.")

    # Route: GitHub URL vs plain CV text
    source = "cv"
    if not file and is_github_url(raw_text.strip()):
        print(f"[API] Detected GitHub URL: {raw_text.strip()}")
        extracted = extract_from_github_url(raw_text.strip())
        source = "github"
    else:
        extracted = extract_from_text(raw_text)

    if "error" in extracted:
        raise HTTPException(status_code=500, detail=extracted["error"])

    # Confidence scoring
    key_fields = ["name", "current_role", "technologies", "seniority",
                  "years_of_experience", "location", "email"]
    filled = sum(1 for f in key_fields if str(extracted.get(f, "") or "").strip())
    ratio = filled / len(key_fields)
    if ratio >= 0.85:
        confidence_level = "high"
    elif ratio >= 0.55:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    # Dedup check
    duplicate = check_duplicate(
        name=extracted.get("name", ""),
        email=extracted.get("email", ""),
        linkedin_url=extracted.get("linkedin_url", "")
    )

    return {
        "extracted_data": extracted,
        "is_duplicate": duplicate is not None,
        "existing_record": duplicate,
        "confidence_level": confidence_level,
        "confidence_ratio": round(ratio * 100),
        "source": source,
        "message": "Review the extracted data. Click 'Approve' to add to the talent pool." if not duplicate
                   else "Candidate may already exist in the pool. Review and choose to merge or add as new."
    }


@app.post("/api/ingest/approve")
async def approve_ingestion(request: IngestApproveRequest):
    """Human-in-the-loop: approve extracted data and write to DB."""
    global db

    candidate_data = request.candidate_data
    duplicate = check_duplicate(
        name=candidate_data.get("name", ""),
        email=candidate_data.get("email", ""),
        linkedin_url=candidate_data.get("linkedin_url", "")
    )

    if duplicate:
        merged = intelligent_merge(duplicate, candidate_data)
        success = update_candidate_in_pool(duplicate["name"], merged)
        action_word = "merged into"
    else:
        success = add_candidate_to_pool(candidate_data)
        action_word = "added to"

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update talent pool.")

    # If a hiring request was specified, create an application
    if request.hiring_request_id:
        session = get_session()
        try:
            app_entry = Application(
                hiring_request_id=request.hiring_request_id,
                candidate_name=candidate_data.get("name", ""),
                source="cv_upload",
                applied_date=datetime.now().strftime("%Y-%m-%d"),
                step="applied",
                category="applicant",
            )
            session.add(app_entry)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    # Rebuild vector DB after adding/merging
    db = build_vector_database()

    return {"message": f"{candidate_data.get('name', 'Candidate')} {action_word} talent pool.", "success": True}


# ═══════════════════════════════════════════
# POOL MAINTENANCE
# ═══════════════════════════════════════════

@app.get("/api/refresh/stale")
async def get_stale():
    """Identify candidates needing refresh (last update > 3 months)."""
    stale = get_stale_candidates(months_threshold=3)
    return {"stale_candidates": stale, "count": len(stale)}


@app.post("/api/refresh/update")
async def refresh_candidates(request: RefreshRequest):
    """Bulk refresh selected candidates (update timestamps)."""
    global db
    result = bulk_refresh_candidates(request.candidate_names)
    db = build_vector_database()
    return result


@app.post("/api/refresh/merge")
async def merge_candidate(request: ManualUpdateRequest):
    """Manually update a candidate with new data (AI powered merge)."""
    global db
    existing = check_duplicate(name=request.candidate_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Candidate not found in pool.")

    merged = intelligent_merge(existing, request.new_data)
    success = update_candidate_in_pool(request.candidate_name, merged)

    if success:
        db = build_vector_database()

    return {"merged_data": merged, "success": success}


# ═══════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════

@app.post("/api/export-shortlist")
async def export_shortlist(request: ExportShortlistRequest):
    """Return a ranked shortlist as a downloadable CSV file."""
    fieldnames = [
        "rank", "name", "role", "matchScore", "matchRank",
        "skillsScore", "expScore", "industryScore", "locationScore", "statusScore",
        "tags", "citation", "github_url"
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for i, cand in enumerate(request.candidates, start=1):
        row = {k: cand.get(k, "") for k in fieldnames}
        row["rank"] = i
        if isinstance(row["tags"], list):
            row["tags"] = ", ".join(row["tags"])
        writer.writerow(row)

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"shortlist_{timestamp}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ═══════════════════════════════════════════
# OUTREACH / ENGAGE
# ═══════════════════════════════════════════

@app.post("/api/draft-email")
async def draft_email(request: EmailDraftRequest):
    """Generate personalized outreach email for a candidate."""
    candidate = check_duplicate(name=request.candidate_name)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    email = generate_email_draft(candidate, request.job_description)
    return {"candidate_name": request.candidate_name, "email_draft": email}


@app.post("/api/draft-followup")
async def draft_followup(request: FollowUpRequest):
    """Generate follow-up email for non-replying candidate."""
    candidate = check_duplicate(name=request.candidate_name)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    followup = generate_followup_draft(candidate)
    return {"candidate_name": request.candidate_name, "followup_draft": followup}


@app.get("/api/outreach-status")
async def get_outreach_status():
    """Get outreach progress monitoring dashboard data."""
    return get_outreach_dashboard()

@app.post("/api/outreach-status")
async def set_outreach_status(request: OutreachStatusUpdate):
    """Update a candidate's outreach status."""
    success = update_outreach_status(request.candidate_name, request.status)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update status.")
    return {"success": True, "message": f"Status updated to '{request.status}'"}


# ═══════════════════════════════════════════
# GITHUB / SOURCES
# ═══════════════════════════════════════════

@app.post("/api/github-search")
async def github_search(request: GitHubSearchRequest):
    """Search GitHub for developer candidates."""
    clean_query, is_safe = sanitize_input(request.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail="Query contains disallowed patterns.")

    if request.search_type == "criteria":
        result = search_by_criteria(clean_query)
    elif request.search_type == "profile":
        result = search_by_profile(clean_query)
    else:
        raise HTTPException(status_code=400, detail="search_type must be 'criteria' or 'profile'")

    return result


# ═══════════════════════════════════════════
# ANALYTICS / METRICS
# ═══════════════════════════════════════════

@app.get("/api/metrics")
async def get_metrics():
    """Success metrics and pool health stats."""
    stats = get_pool_stats()
    outreach = get_outreach_dashboard()

    return {
        "pool_stats": stats,
        "outreach_summary": outreach.get("summary", {}),
        "target_accuracy": "80%",
        "evaluation_framework": "LangChain-based (as recommended by Linnify)",
    }


# ═══════════════════════════════════════════
# LINNIFY API STUB
# ═══════════════════════════════════════════

@app.get("/api/linnify/jobs")
async def linnify_jobs_stub():
    """Stub endpoint for Linnify API integration.
    When Linnify provides their API, this will proxy/sync their job data."""
    return {
        "source": "linnify",
        "status": "stub",
        "message": "Linnify API integration pending. Using local demo data.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)