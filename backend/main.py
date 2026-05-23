"""
FastAPI Backend

All 12 API endpoints for the AI Talent Pool Manager.

"""
import os
import csv
import json
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from ai.RAG_engine import build_vector_database, create_retriever_chain
from ai.cv_ingestion import extract_from_text, check_duplicate, add_candidate_to_csv, update_candidate_in_csv
from ai.pool_maintenance import get_stale_candidates, intelligent_merge, bulk_refresh_candidates, get_pool_stats
from ai.outreach_agent import generate_email_draft, generate_followup_draft, update_outreach_status, get_outreach_dashboard
from ai.linkedin_sourcing import search_by_role, search_by_profile
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

print("Initializing Retriever Chain...")
matcher = create_retriever_chain(db) if db else None

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

class LinkedInSearchRequest(BaseModel):
    query: str
    search_type: str  # "role" or "profile"

class ManualUpdateRequest(BaseModel):
    candidate_name: str
    new_data: dict

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

# ENDPOINT: POST /api/match —  Shortlisting

@app.post("/api/match")
async def match_candidates(request: MatchRequest):
    # Shortlist candidates from talent pool based on job query.
    # Guardrail: sanitize input
    clean_query, is_safe = sanitize_input(request.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail="Query contains disallowed patterns.")
    
    if not matcher:
        return []
    
    print(f"\n[API] Match query: {clean_query}")
    try:
        candidates = matcher.invoke({"input": clean_query})
        print(f"[API] Found {len(candidates) if isinstance(candidates, list) else 0} matches")
        
        if not candidates:
            return []
        if isinstance(candidates, dict):
            candidates = [candidates]
        
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
        "message": "Review the extracted data. Click 'Approve' to add to the talent pool." if not duplicate
                   else "Candidate may already exist in the pool. Review and choose to merge or add as new."
    }

# ENDPOINT: POST /api/ingest/approve — Human approves extraction

@app.post("/api/ingest/approve")
async def approve_ingestion(request: IngestApproveRequest):
    # Human-in-the-loop: approve extracted data and write to CSV.
    global db, matcher
    
    success = add_candidate_to_csv(request.candidate_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write to CSV.")
    
    # Rebuild vector DB after adding new candidate
    db = build_vector_database()
    matcher = create_retriever_chain(db) if db else None
    
    return {"message": f" {request.candidate_data.get('name', 'Candidate')} added to talent pool.", "success": True}

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
    global db, matcher
    
    result = bulk_refresh_candidates(request.candidate_names)
    
    # Rebuild vector DB after refresh
    db = build_vector_database()
    matcher = create_retriever_chain(db) if db else None
    
    return result

# ENDPOINT: POST /api/refresh/merge - manual update + merge

@app.post("/api/refresh/merge")
async def merge_candidate(request: ManualUpdateRequest):
    # Manually update a candidate with new data (AI powered merge).
    global db, matcher
    
    existing = check_duplicate(name=request.candidate_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Candidate not found in pool.")
    
    merged = intelligent_merge(existing, request.new_data)
    success = update_candidate_in_csv(request.candidate_name, merged)
    
    if success:
        db = build_vector_database()
        matcher = create_retriever_chain(db) if db else None
    
    return {"merged_data": merged, "success": success}

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

# ENDPOINT: POST /api/linkedin-search -LinkedIn sourcing

@app.post("/api/linkedin-search")
async def linkedin_search(request: LinkedInSearchRequest):
    # Generate LinkedIn search strategy (by role or by profile).
    clean_query, is_safe = sanitize_input(request.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail="Query contains disallowed patterns.")
    
    if request.search_type == "role":
        result = search_by_role(clean_query)
    elif request.search_type == "profile":
        result = search_by_profile(clean_query)
    else:
        raise HTTPException(status_code=400, detail="search_type must be 'role' or 'profile'")
    
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