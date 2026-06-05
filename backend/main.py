"""
FastAPI Backend

All 12 API endpoints for the AI Talent Pool Manager.

"""
import io
import os
import csv
import json
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from ai.RAG_engine import build_vector_database, score_shortlist
from ai.cv_ingestion import extract_from_text, check_duplicate, add_candidate_to_csv, update_candidate_in_csv
from ai.pool_maintenance import get_stale_candidates, intelligent_merge, bulk_refresh_candidates, get_pool_stats
from ai.outreach_agent import generate_email_draft, generate_followup_draft, update_outreach_status, get_outreach_dashboard
from ai.github_sourcing import search_by_criteria, search_by_profile
from ai.guardrails import sanitize_input
from scraper.parser import extract_text_from_pdf

app = FastAPI(title="TalentAI Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))

# Initialize RAG
print("Initializing Vector Database from CSV...")
db = build_vector_database()
if db:
    print("Vector database built successfully from talent_pool.csv")
else:
    print("Warning: Vector database could not be built. Run migration script first.")

# Models

class MatchRequest(BaseModel):
    query: str

class IngestApproveRequest(BaseModel):
    candidate_data: dict

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

# ENDPOINT: GET /api/candidates — Dashboard table

@app.get("/api/candidates")
async def get_candidates():
    # Return all candidates from CSV for the dashboard table.
    if not CSV_PATH.exists():
        return []
    
    candidates = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidates.append(row)
    
    return candidates

# ENDPOINT: POST /api/match —  Shortlisting (deterministic scorer)

@app.post("/api/match")
async def match_candidates(request: MatchRequest):
    """Shortlist candidates using the weighted scoring pipeline.
    
    Flow: LLM parses JD → vector DB retrieves candidates → deterministic
    scorer ranks them with weighted formula → returns top 3.
    """
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

# ENDPOINT: POST /api/ingest — CV Extraction

@app.post("/api/ingest")
async def ingest_cv(file: UploadFile = File(None), text: str = Form(None)):
    
    #Upload a CV (PDF) or paste LinkedIn text.
    #AI extracts fields → returns preview for human approval.
    
    raw_text = ""
    
    if file:
        # Save uploaded PDF temporarily and extract text
        suffix = Path(file.filename).suffix if file.filename else ".pdf"
        tmp_dir = BASE_DIR / "data" / "uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
        
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        
        raw_text = extract_text_from_pdf(str(tmp_path))
        
        # Clean up temp file
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
    
    # AI extraction 
    extracted = extract_from_text(raw_text)
    
    if "error" in extracted:
        raise HTTPException(status_code=500, detail=extracted["error"])
    
    # Confidence scoring — count populated fields
    key_fields = ["name", "current_role", "technologies", "seniority",
                  "years_of_experience", "location", "email"]
    filled = sum(1 for f in key_fields if extracted.get(f, "").strip())
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
        "message": "Review the extracted data. Click 'Approve' to add to the talent pool." if not duplicate
                   else "Candidate may already exist in the pool. Review and choose to merge or add as new."
    }

# ENDPOINT: POST /api/ingest/approve — Human approves extraction

@app.post("/api/ingest/approve")
async def approve_ingestion(request: IngestApproveRequest):
    # Human-in-the-loop: approve extracted data and write to CSV.
    global db
    
    candidate_data = request.candidate_data
    # Check if this is an existing candidate
    duplicate = check_duplicate(
        name=candidate_data.get("name", ""),
        email=candidate_data.get("email", ""),
        linkedin_url=candidate_data.get("linkedin_url", "")
    )
    
    if duplicate:
        # Merge operation
        merged = intelligent_merge(duplicate, candidate_data)
        success = update_candidate_in_csv(duplicate["name"], merged)
        action_word = "merged into"
    else:
        # New candidate
        success = add_candidate_to_csv(candidate_data)
        action_word = "added to"

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update talent pool CSV.")
    
    # Rebuild vector DB after adding/merging
    db = build_vector_database()
    
    return {"message": f" {candidate_data.get('name', 'Candidate')} {action_word} talent pool.", "success": True}

# ENDPOINT: GET /api/refresh/stale, auto-update detection

@app.get("/api/refresh/stale")
async def get_stale():
    #Identify candidates needing refresh (last update > 3 months).
    stale = get_stale_candidates(months_threshold=3)
    return {"stale_candidates": stale, "count": len(stale)}

# ENDPOINT: POST /api/refresh/update, bulk refresh

@app.post("/api/refresh/update")
async def refresh_candidates(request: RefreshRequest):
    # Bulk refresh selected candidates (update timestamps).
    global db
    
    result = bulk_refresh_candidates(request.candidate_names)
    
    # Rebuild vector DB after refresh
    db = build_vector_database()
    
    return result

# ENDPOINT: POST /api/refresh/merge - manual update + merge

@app.post("/api/refresh/merge")
async def merge_candidate(request: ManualUpdateRequest):
    # Manually update a candidate with new data (AI powered merge).
    global db
    
    existing = check_duplicate(name=request.candidate_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Candidate not found in pool.")
    
    merged = intelligent_merge(existing, request.new_data)
    success = update_candidate_in_csv(request.candidate_name, merged)
    
    if success:
        db = build_vector_database()
    
    return {"merged_data": merged, "success": success}


# ENDPOINT: POST /api/export-shortlist — Download shortlist as CSV

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

# ENDPOINT: POST /api/draft-email- Email drafts

@app.post("/api/draft-email")
async def draft_email(request: EmailDraftRequest):
    # Generate personalized outreach email for a candidate.
    # Find candidate in CSV
    candidate = check_duplicate(name=request.candidate_name)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    
    email = generate_email_draft(candidate, request.job_description)
    return {"candidate_name": request.candidate_name, "email_draft": email}

# ENDPOINT: POST /api/draft-followup - follow-up drafts

@app.post("/api/draft-followup")
async def draft_followup(request: FollowUpRequest):
    # Generate follow-up email for non-replying candidate.
    candidate = check_duplicate(name=request.candidate_name)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    
    followup = generate_followup_draft(candidate)
    return {"candidate_name": request.candidate_name, "followup_draft": followup}

# ENDPOINT: GET + POST /api/outreach-status — Progress monitoring

@app.get("/api/outreach-status")
async def get_outreach_status():
    # Get outreach progress monitoring dashboard data.
    return get_outreach_dashboard()

@app.post("/api/outreach-status")
async def set_outreach_status(request: OutreachStatusUpdate):
    # Update a candidate's outreach status.
    success = update_outreach_status(request.candidate_name, request.status)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update status.")
    return {"success": True, "message": f"Status updated to '{request.status}'"}

# ENDPOINT: POST /api/github-search — GitHub sourcing

@app.post("/api/github-search")
async def github_search(request: GitHubSearchRequest):
    # Search GitHub for developer candidates.
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

# ENDPOINT: GET /api/metrics — Success metrics dashboard
@app.get("/api/metrics")
async def get_metrics():
    #Success metrics and pool health stats.
    stats = get_pool_stats()
    outreach = get_outreach_dashboard()
    
    return {
        "pool_stats": stats,
        "outreach_summary": outreach.get("summary", {}),
        "target_accuracy": "80%",
        "evaluation_framework": "LangChain-based (as recommended by Linnify)",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)