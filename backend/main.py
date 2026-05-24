"""
FastAPI Backend — AI Talent Pool Manager.

13+ API endpoints covering the 4 Linnify modules plus governance:
  - Module 1: ingest (CV/LinkedIn extraction with HITL approval)
  - Module 2: refresh / merge (real re-extraction from source + intelligent merge)
  - Module 3: outreach drafts + follow-ups + status tracking
  - Module 4: shortlist match + LinkedIn sourcing strategies
  - Governance: metrics with real eval, audit log, provider info
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.audit_log import log_action, read_audit
from ai.cv_ingestion import (
    add_candidate_to_csv,
    check_duplicate,
    extract_from_text,
    update_candidate_in_csv,
)
from ai.guardrails import sanitize_input
from ai.linkedin_sourcing import search_by_profile, search_by_role
from ai.llm_provider import get_provider_status
from ai.outreach_agent import (
    generate_email_draft,
    generate_followup_draft,
    get_outreach_dashboard,
    update_outreach_status,
)
from ai.pii import mask_candidate_row
from ai.pool_maintenance import (
    bulk_refresh_candidates,
    get_pool_stats,
    get_stale_candidates,
    intelligent_merge,
)
from ai.RAG_engine import (
    build_vector_database,
    create_retriever_chain,
    remove_candidate,
    upsert_candidate,
)
from evals.evaluator import load_last_run, run_evaluation
from scraper.parser import extract_text_from_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("talentai")

app = FastAPI(title="TalentAI Agent", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))

# ---------------------------------------------------------------------------
# Vector DB / matcher bootstrap (now persistent + incremental — see RAG_engine).
# ---------------------------------------------------------------------------
logger.info("Initializing vector database from CSV…")
db = build_vector_database()
matcher = create_retriever_chain(db) if db else None
if db is None:
    logger.warning("Vector DB unavailable. Make sure data/talent_pool.csv exists.")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/api/candidates")
async def get_candidates(reveal_pii: bool = Query(False, description="Set to true to include unmasked email")):
    """Return talent pool. PII (email) is masked by default — pass reveal_pii=true to opt out.

    The audit log records every reveal so we have traceability if data is later
    leaked or mishandled."""
    if not CSV_PATH.exists():
        return []

    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row if reveal_pii else mask_candidate_row(row))

    if reveal_pii:
        log_action("pii_reveal", actor="human", target=None, details={"row_count": len(rows)})

    return rows


@app.get("/api/candidates/{name}/contact")
async def get_candidate_contact(name: str):
    """Return unmasked contact info for a single candidate. Logged in audit trail."""
    existing = check_duplicate(name=name)
    if not existing:
        raise HTTPException(status_code=404, detail="Candidate not found")
    log_action("pii_contact_reveal", actor="human", target=name)
    return {
        "name": existing.get("name"),
        "email": existing.get("email", ""),
        "linkedin_url": existing.get("linkedin_url", ""),
        "github_url": existing.get("github_url", ""),
    }


# ---------------------------------------------------------------------------
# Module 4 — Shortlisting
# ---------------------------------------------------------------------------

@app.post("/api/match")
async def match_candidates(request: MatchRequest):
    clean_query, is_safe = sanitize_input(request.query)
    if not is_safe:
        log_action("match_rejected", actor="agent", details={"reason": "injection_pattern"})
        raise HTTPException(status_code=400, detail="Query contains disallowed patterns.")

    if not matcher:
        return []

    logger.info("Match query: %s", clean_query)
    try:
        candidates = matcher.invoke({"input": clean_query})
        if not candidates:
            log_action("match", actor="agent", details={"query": clean_query, "result_count": 0})
            return []
        if isinstance(candidates, dict):
            candidates = [candidates]
        log_action(
            "match",
            actor="agent",
            details={"query": clean_query, "result_count": len(candidates),
                     "candidate_names": [c.get("name") for c in candidates if isinstance(c, dict)]},
        )
        return candidates
    except Exception as e:
        logger.exception("Match error")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Module 1 — Ingest
# ---------------------------------------------------------------------------

@app.post("/api/ingest")
async def ingest_cv(file: UploadFile = File(None), text: str = Form(None)):
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

    extracted = extract_from_text(raw_text)
    if "error" in extracted:
        raise HTTPException(status_code=500, detail=extracted["error"])

    duplicate = check_duplicate(
        name=extracted.get("name", ""),
        email=extracted.get("email", ""),
        linkedin_url=extracted.get("linkedin_url", ""),
    )

    log_action(
        "ingest_extract",
        actor="agent",
        target=extracted.get("name", "unknown"),
        details={"is_duplicate": duplicate is not None, "source": "file" if file else "text"},
    )

    return {
        "extracted_data": extracted,
        "is_duplicate": duplicate is not None,
        "existing_record": duplicate,
        "message": (
            "Review the extracted data. Click 'Approve' to add to the talent pool."
            if not duplicate
            else "Candidate may already exist in the pool. Review and choose to merge or add as new."
        ),
    }


@app.post("/api/ingest/approve")
async def approve_ingestion(request: IngestApproveRequest):
    """Human-in-the-loop: write the reviewed candidate to CSV and update the vector store."""
    global db, matcher

    success = add_candidate_to_csv(request.candidate_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write to CSV.")

    # Incremental update — no full Chroma rebuild.
    if db is not None:
        upsert_candidate(request.candidate_data, db)
    else:
        db = build_vector_database()
        matcher = create_retriever_chain(db) if db else None

    log_action(
        "ingest_approve",
        actor="human",
        target=request.candidate_data.get("name"),
        details={"fields_provided": list(request.candidate_data.keys())},
    )

    return {
        "message": f"{request.candidate_data.get('name', 'Candidate')} added to talent pool.",
        "success": True,
    }


# ---------------------------------------------------------------------------
# Module 2 — Pool maintenance
# ---------------------------------------------------------------------------

@app.get("/api/refresh/stale")
async def get_stale():
    stale = get_stale_candidates(months_threshold=3)
    return {"stale_candidates": stale, "count": len(stale)}


@app.post("/api/refresh/update")
async def refresh_candidates(request: RefreshRequest):
    global db, matcher

    result = bulk_refresh_candidates(request.candidate_names)

    # Re-index only the affected candidates instead of rebuilding everything.
    if db is not None and CSV_PATH.exists():
        normalized_names = {c["name"] for c in (result.get("normalized") or [])}
        timestamp_names = set(result.get("timestamp_only") or [])
        names_to_update = normalized_names | timestamp_names
        if names_to_update:
            with open(CSV_PATH, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("name", "").strip() in names_to_update:
                        upsert_candidate(row, db)

    log_action(
        "bulk_refresh",
        actor="human",
        details={
            "requested": request.candidate_names,
            "normalized": result.get("normalized"),
            "timestamp_only": result.get("timestamp_only"),
        },
    )
    return result


@app.post("/api/refresh/merge")
async def merge_candidate(request: ManualUpdateRequest):
    global db, matcher

    existing = check_duplicate(name=request.candidate_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Candidate not found in pool.")

    merged = intelligent_merge(existing, request.new_data)
    success = update_candidate_in_csv(request.candidate_name, merged)

    if success and db is not None:
        upsert_candidate(merged, db)

    log_action(
        "manual_merge",
        actor="human",
        target=request.candidate_name,
        details={"fields_updated": list(request.new_data.keys())},
    )
    return {"merged_data": merged, "success": success}


# ---------------------------------------------------------------------------
# Module 3 — Outreach
# ---------------------------------------------------------------------------

@app.post("/api/draft-email")
async def draft_email(request: EmailDraftRequest):
    candidate = check_duplicate(name=request.candidate_name)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    email = generate_email_draft(candidate, request.job_description)
    log_action(
        "email_draft",
        actor="agent",
        target=request.candidate_name,
        details={"job_description_preview": request.job_description[:120]},
    )
    return {
        "candidate_name": request.candidate_name,
        "email_draft": email,
        "note": "DRAFT ONLY — the system never sends emails. The HR user must send manually.",
    }


@app.post("/api/draft-followup")
async def draft_followup(request: FollowUpRequest):
    candidate = check_duplicate(name=request.candidate_name)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    followup = generate_followup_draft(candidate)
    log_action("followup_draft", actor="agent", target=request.candidate_name)
    return {
        "candidate_name": request.candidate_name,
        "followup_draft": followup,
        "note": "DRAFT ONLY — never auto-sent.",
    }


@app.get("/api/outreach-status")
async def get_outreach_status():
    return get_outreach_dashboard()


@app.post("/api/outreach-status")
async def set_outreach_status(request: OutreachStatusUpdate):
    success = update_outreach_status(request.candidate_name, request.status)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update status.")
    log_action(
        "outreach_status_change",
        actor="human",
        target=request.candidate_name,
        details={"new_status": request.status},
    )
    return {"success": True, "message": f"Status updated to '{request.status}'"}


# ---------------------------------------------------------------------------
# Module 4 — LinkedIn sourcing strategies
# ---------------------------------------------------------------------------

@app.post("/api/linkedin-search")
async def linkedin_search(request: LinkedInSearchRequest):
    clean_query, is_safe = sanitize_input(request.query)
    if not is_safe:
        raise HTTPException(status_code=400, detail="Query contains disallowed patterns.")

    if request.search_type == "role":
        result = search_by_role(clean_query)
    elif request.search_type == "profile":
        result = search_by_profile(clean_query)
    else:
        raise HTTPException(status_code=400, detail="search_type must be 'role' or 'profile'")

    log_action(
        "linkedin_search",
        actor="agent",
        details={"search_type": request.search_type, "query_preview": clean_query[:120]},
    )
    return result


# ---------------------------------------------------------------------------
# Governance — metrics, eval, audit, provider info
# ---------------------------------------------------------------------------

@app.get("/api/metrics")
async def get_metrics():
    """Pool stats + outreach summary + last eval result + LLM provider info."""
    stats = get_pool_stats()
    outreach = get_outreach_dashboard()
    last_eval = load_last_run()
    provider = get_provider_status()

    return {
        "pool_stats": stats,
        "outreach_summary": outreach.get("summary", {}),
        "llm_provider": provider,
        "evaluation_framework": (
            "LangChain-compatible evaluator (precision@k, recall@k, MRR, hit-rate, leak-rate). "
            "Ground truth: backend/evals/ground_truth.json"
        ),
        "target_accuracy": 0.80,
        "last_evaluation": last_eval,
    }


@app.post("/api/evaluate")
async def trigger_evaluation(k: int = Query(3, ge=1, le=10)):
    """Run the shortlisting eval against ground_truth.json. May take ~30s on Groq."""
    if matcher is None:
        raise HTTPException(status_code=503, detail="Matcher not available.")

    def invoke(query: str):
        return matcher.invoke({"input": query})

    result = run_evaluation(invoke, k=k)
    agg = result.get("aggregated", {})
    log_action(
        "evaluation_run",
        actor="human",
        details={
            "k": k,
            "accuracy": agg.get("accuracy"),
            "mrr": agg.get("mrr"),
            "meets_target": agg.get("meets_target"),
        },
    )
    return result


@app.get("/api/audit")
async def get_audit(limit: int = Query(100, ge=1, le=1000), action: Optional[str] = None):
    """Return recent audit log entries (newest first). Optional `action` filter."""
    return {"entries": read_audit(limit=limit, action_filter=action)}


@app.get("/api/provider")
async def get_provider():
    """Surface the active LLM provider so the UI can show a GDPR badge."""
    return get_provider_status()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
