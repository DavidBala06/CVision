"""
RAG Engine

Shortlisting — scan talent pool CSV, rank candidates for a job.

Pipeline:
  1. LLM parses the job description into structured requirements
  2. Vector DB retrieves semantically similar candidate profiles
  3. Deterministic scorer (scorer.py) computes weighted scores
  4. Return top N candidates ranked by matchScore

The LLM is used ONLY for JD parsing — all scoring is deterministic
and auditable via the weighted formula in scorer.py.
"""
import os
import csv
import warnings
from pathlib import Path
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.documents import Document

from ai.scorer import parse_job_description, rank_candidates

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))
CHROMA_DB_PATH = str(BASE_DIR / "chroma_csv_storage")


def load_csv_as_documents() -> list[Document]:
    # Load each CSV row as a LangChain Document for vector indexing.
    if not CSV_PATH.exists():
        print(f"CSV not found at {CSV_PATH}")
        return []

    documents = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Build rich text content from all fields
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
            
            # Filter out empty fields
            content = "\n".join(p for p in content_parts if not p.endswith(": "))
            
            metadata = {
                "name": row.get("name", ""),
                "seniority": row.get("seniority", ""),
                "years_of_experience": row.get("years_of_experience", ""),
                "current_role": row.get("current_role", ""),
                "previous_jobs": row.get("previous_jobs", ""),
                "degrees": row.get("degrees", ""),
                "location": row.get("location", ""),
                "languages": row.get("languages", ""),
                "technologies": row.get("technologies", ""),
                "project_summary": row.get("project_summary", ""),
                "linkedin_url": row.get("linkedin_url", ""),
                "github_url": row.get("github_url", ""),
                "email": row.get("email", ""),
                "status": row.get("status", ""),
                "last_updated_at": row.get("last_updated_at", ""),
            }
            
            documents.append(Document(page_content=content, metadata=metadata))

    return documents


def build_vector_database():
    #Build Chroma vector database from CSV talent pool.
    print(f"Loading talent pool from: {CSV_PATH}")

    documents = load_csv_as_documents()

    if not documents:
        print(f"No candidates found in CSV at '{CSV_PATH}'")
        return None

    print(f"Loaded {len(documents)} candidate profiles from CSV.")

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    # Rebuild vector store each time (CSV is small, fast to index)
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )
    return vector_db


def _get_llm():
    """Shared LLM instance for JD parsing."""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=1024,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )


def score_shortlist(query: str, vector_db, top_n: int = 3) -> list[dict]:
    """
    Full shortlisting pipeline:
      1. LLM parses the query into structured requirements
      2. Vector DB retrieves candidate documents (semantic search)
      3. Deterministic scorer ranks them with weighted formula
      4. Returns top N candidates

    Returns:
        list of scored candidate dicts ready for the frontend CandidateCard
    """
    if vector_db is None:
        return []

    llm = _get_llm()

    # Step 1: Parse JD into structured requirements
    print(f"  [Scorer] Parsing JD with LLM...")
    requirements = parse_job_description(query, llm)
    print(f"  [Scorer] Requirements: skills={requirements.get('required_skills', [])}, "
          f"seniority={requirements.get('min_seniority')}, "
          f"industry={requirements.get('industry')}, "
          f"location={requirements.get('location')}")

    # Step 2: Retrieve candidate documents (score all candidates for deterministic strictness)
    docs = load_csv_as_documents()
    print(f"  [Scorer] Retrieved {len(docs)} candidate docs from CSV for full scoring")

    # Convert documents back to dicts for the scorer
    candidate_dicts = []
    for doc in docs:
        candidate_dicts.append(doc.metadata)

    if not candidate_dicts:
        return []

    # Step 3: Deterministic scoring
    print(f"  [Scorer] Scoring {len(candidate_dicts)} candidates with weighted formula...")
    results = rank_candidates(candidate_dicts, requirements, top_n=top_n)

    for r in results:
        print(f"    {r['name']:30s}  matchScore={r['matchScore']}  "
              f"skills={r['skillsScore']}  exp={r['expScore']}  "
              f"industry={r['industryScore']}  loc={r['locationScore']}")

    return results


# ---------------------------------------------------------------------------
# Backward compatibility — keep create_retriever_chain for anything that
# still references it, but it now just returns a thin wrapper.
# ---------------------------------------------------------------------------

def create_retriever_chain(vector_db):
    """Legacy wrapper. Returns None — use score_shortlist() directly."""
    return None