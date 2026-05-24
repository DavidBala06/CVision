"""
RAG Engine — Module 4 shortlisting.

Scans the talent pool CSV, embeds each row, and uses a vector store + chat LLM
to rank candidates for a job query.

Improvements over the original version:
  - Persistent Chroma (no full rebuild on every ingest)
  - LLM provider abstraction (Groq / Mistral EU / Ollama / HuggingFace)
  - Deterministic weighted scorer (45/20/15/15/5) instead of LLM-subjective numbers
  - Stable per-candidate ids so vectors can be incrementally added/replaced
"""
from __future__ import annotations

import csv
import hashlib
import logging
import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from ai.llm_provider import get_chat_llm
from ai.scorer import parse_job_description, rank_candidates

load_dotenv()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))
CHROMA_DB_PATH = str(BASE_DIR / "chroma_csv_storage")
COLLECTION_NAME = "talent_pool"

def _stable_id(name: str) -> str:
    """Generate a deterministic id from candidate name so re-ingest replaces, not duplicates."""
    return hashlib.sha1(name.strip().lower().encode("utf-8")).hexdigest()[:16]


def _row_to_document(row: dict) -> Document:
    """Convert a CSV row to a LangChain Document with full content + safe metadata."""
    content_parts = [
        f"Name: {row.get('name', '')}",
        f"Seniority: {row.get('seniority', '')}",
        f"Years of Experience: {row.get('years_of_experience', '')}",
        f"Current Role: {row.get('current_role', '')}",
        f"Previous Jobs: {row.get('previous_jobs', '')}",
        f"Degrees: {row.get('degrees', '')}",
        f"Location: {row.get('location', '')}",
        f"Languages: {row.get('languages', '')}",
        f"Technologies: {row.get('technologies', '')}",
        f"Project Summary: {row.get('project_summary', '')}",
    ]
    content = "\n".join(p for p in content_parts if not p.endswith(": "))

    metadata = {
        "id": _stable_id(row.get("name", "")),
        "name": row.get("name", ""),
        "seniority": row.get("seniority", ""),
        "location": row.get("location", ""),
        "technologies": row.get("technologies", ""),
        "linkedin_url": row.get("linkedin_url", ""),
        "github_url": row.get("github_url", ""),
        "email": row.get("email", ""),
        "status": row.get("status", ""),
    }
    return Document(page_content=content, metadata=metadata)


def load_csv_as_documents() -> list[Document]:
    if not CSV_PATH.exists():
        logger.warning("CSV not found at %s", CSV_PATH)
        return []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [_row_to_document(row) for row in reader]


def _get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vector_database():
    """Build (or reuse) the Chroma vector database from the CSV talent pool.

    If the persisted index already covers the current CSV rows, we simply
    open it — no expensive re-embedding. Otherwise we add only the missing
    documents instead of rebuilding from scratch.
    """
    logger.info("Loading talent pool from: %s", CSV_PATH)
    documents = load_csv_as_documents()
    if not documents:
        logger.warning("No candidates found in CSV at '%s'", CSV_PATH)
        return None

    logger.info("Loaded %d candidate profiles from CSV.", len(documents))
    embeddings = _get_embeddings()

    persist_dir = Path(CHROMA_DB_PATH)
    persist_dir.mkdir(parents=True, exist_ok=True)

    vector_db = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH,
        collection_metadata={"hnsw:space": "cosine"},
    )

    # Reconcile: which ids are already indexed?
    existing_ids: set[str] = set()
    try:
        existing = vector_db.get()  # returns {'ids': [...], 'metadatas': [...]}
        existing_ids = set(existing.get("ids") or [])
    except Exception as e:
        logger.debug("Could not enumerate existing Chroma ids (fresh DB?): %s", e)

    new_docs: list[Document] = []
    new_ids: list[str] = []
    for doc in documents:
        doc_id = doc.metadata.get("id")
        if doc_id and doc_id not in existing_ids:
            new_docs.append(doc)
            new_ids.append(doc_id)

    if new_docs:
        logger.info("Adding %d new documents to Chroma (had %d).", len(new_docs), len(existing_ids))
        vector_db.add_documents(documents=new_docs, ids=new_ids)
    else:
        logger.info("Chroma index is up to date (%d docs).", len(existing_ids))

    return vector_db


def upsert_candidate(row: dict, vector_db) -> None:
    """Insert or replace a single candidate's vector. Called after ingest/merge."""
    if vector_db is None:
        return
    doc = _row_to_document(row)
    doc_id = doc.metadata["id"]
    try:
        vector_db.delete(ids=[doc_id])
    except Exception:
        pass
    vector_db.add_documents(documents=[doc], ids=[doc_id])


def remove_candidate(name: str, vector_db) -> None:
    if vector_db is None or not name:
        return
    try:
        vector_db.delete(ids=[_stable_id(name)])
    except Exception as e:
        logger.warning("Failed to remove %s from vector store: %s", name, e)


def _candidate_from_metadata(doc: Document, full_rows: dict) -> dict:
    """Re-hydrate the full CSV row from the in-memory cache (full_rows by name)."""
    name = doc.metadata.get("name", "")
    return full_rows.get(name) or {**doc.metadata, "technologies": doc.metadata.get("technologies", "")}


def _load_full_rows() -> dict[str, dict]:
    """Load the CSV again so scorer has access to every field (project_summary,
    previous_jobs, etc.) — Chroma metadata is intentionally minimal."""
    rows = {}
    if not CSV_PATH.exists():
        return rows
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row.get("name", "")] = row
    return rows


def create_retriever_chain(vector_db):
    """Build the shortlisting pipeline.

    Pipeline:
      query → LLM parses requirements → Chroma retrieves top-K (broad recall)
            → deterministic weighted scorer → top-3 sorted by matchScore
    """
    if vector_db is None:
        return None

    llm = get_chat_llm(temperature=0.01, max_tokens=1024)
    retriever = vector_db.as_retriever(search_kwargs={"k": 8})

    class _MatchChain:
        """Tiny callable holding the retriever; exposes `.invoke({"input": query})`
        so it matches the LangChain Runnable surface the rest of the code expects."""

        def invoke(self, payload: dict) -> list[dict]:
            query = payload["input"]
            requirements = parse_job_description(query, llm)
            logger.info("Parsed JD requirements: %s", requirements)

            docs = retriever.get_relevant_documents(query)
            full_rows = _load_full_rows()
            candidates = [_candidate_from_metadata(d, full_rows) for d in docs]

            ranked = rank_candidates(candidates, requirements, top_n=3)
            return ranked

    return _MatchChain()
