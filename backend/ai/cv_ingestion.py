"""
CV Ingestion Module 

Handles:
Manual CV/LinkedIn extraction → structured JSON mapped to CSV columns
GitHub profile URL → GitHub API fetch → structured JSON (no LLM needed)
All required fields (name, seniority, years_exp, etc.)

Also performs dedup checking against existing talent pool.
"""
import os
import re
import csv
import json
from pathlib import Path
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from ai.guardrails import sanitize_input, validate_json_output, get_system_guardrail_prompt

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))

# CSV columns that the LLM must extract
EXTRACTION_FIELDS = [
    "name", "seniority", "years_of_experience", "current_role",
    "previous_jobs", "degrees", "location", "languages",
    "technologies", "project_summary", "linkedin_url", "email"
]


def get_llm():
    # Initialize Groq LLM.
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.01,
        max_tokens=2048,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )


def extract_from_text(raw_text: str) -> dict:
    """
    Uses LLM as automatic NER to parse unstructured text into structured fields.
    Returns a dict mapped to CSV columns for human-in-the-loop preview.
    """
    if not raw_text or not raw_text.strip():
        return {"error": "No text provided"}
    
    llm = get_llm()
    parser = JsonOutputParser()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are an expert HR data extraction agent. Your task is to extract structured candidate information from raw CV or LinkedIn profile text.

EXTRACTION RULES:
1. Extract ONLY information that is explicitly stated in the text.
2. If a field is not found, use an empty string "".
3. For 'seniority', classify as: "intern", "junior", "mid", "senior", or "lead" based on years of experience and job titles.
4. For 'years_of_experience', calculate from the earliest job date to now. Use a number.
5. For 'previous_jobs', format as: "Role @ Company; Role @ Company" (most recent first).
6. For 'degrees', format as: "level: Field @ University" (e.g., "bachelor: Computer Science @ MIT").
7. For 'languages', format as: "lang (level), lang (level)" (e.g., "en (native), ro (fluent)").
8. For 'technologies', list as comma-separated lowercase (e.g., "python, javascript, react").
9. For 'project_summary', provide a brief 1-2 sentence summary of key projects.
10. For 'linkedin_url', extract the full LinkedIn profile URL if present.
11. For 'email', extract email address if present.

{format_instructions}
"""),
        ("human", "Extract candidate information from this CV/LinkedIn text:\n\n{text}")
    ])
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "text": raw_text[:5000],  # Limit input size
            "format_instructions": f"Return a JSON object with exactly these keys: {json.dumps(EXTRACTION_FIELDS)}"
        })
        
        # Validate output
        if isinstance(result, dict):
            # Ensure all required fields exist
            for field in EXTRACTION_FIELDS:
                if field not in result:
                    result[field] = ""
            # Infer role from experience if not explicitly stated
            current_role = str(result.get("current_role", "") or "").strip()
            if not current_role:
                inferred = infer_role_from_experience(result)
                if inferred:
                    result["current_role"] = inferred
                    print(f"[Ingestion] Inferred role: {inferred}")
            return result
        
        return {"error": "LLM returned invalid format"}
        
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}


def infer_role_from_experience(extracted: dict) -> str:
    """
    Use the LLM to infer a current role/title when one isn't explicitly stated
    in the CV. Looks at previous_jobs, technologies, seniority, and project_summary
    to generate a fitting role title.

    Returns the inferred role string, or "" if inference fails.
    """
    previous_jobs = str(extracted.get("previous_jobs", "") or "").strip()
    technologies = str(extracted.get("technologies", "") or "").strip()
    seniority = str(extracted.get("seniority", "") or "").strip()
    project_summary = str(extracted.get("project_summary", "") or "").strip()

    # Need at least some context to infer from
    if not previous_jobs and not technologies:
        return ""

    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are an expert HR role classification agent. Based on a candidate's experience,
technologies, and seniority, generate the SINGLE most appropriate current job title.

RULES:
1. Return ONLY the job title, nothing else. No quotes, no explanation.
2. Use standard industry titles (e.g. "Full-Stack Developer", "Data Engineer",
   "DevOps Engineer", "Product Manager", "ML Engineer", "QA Engineer").
3. Include seniority prefix if appropriate (e.g. "Senior Backend Developer",
   "Junior Frontend Developer", "Lead Data Scientist").
4. If the candidate has diverse experience, pick the title that best represents
   their strongest/most recent skill set.
5. Keep it concise — max 5 words.
"""),
        ("human", """Infer the most fitting current job title for this candidate:

PREVIOUS JOBS: {previous_jobs}
TECHNOLOGIES: {technologies}
SENIORITY: {seniority}
PROJECT SUMMARY: {project_summary}

Job title:""")
    ])

    chain = prompt | llm | StrOutputParser()

    try:
        role = chain.invoke({
            "previous_jobs": previous_jobs[:500],
            "technologies": technologies[:300],
            "seniority": seniority,
            "project_summary": project_summary[:300],
        }).strip().strip('"').strip("'")
        # Sanity check: role should be short and not contain explanations
        if role and len(role) < 60 and "\n" not in role:
            return role
        return ""
    except Exception as e:
        print(f"[Ingestion] Role inference failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# GitHub Profile ingestion (no LLM — pure API mapping)
# ---------------------------------------------------------------------------

def is_github_url(text: str) -> bool:
    """Return True if the text looks like a GitHub profile URL or bare username path."""
    text = text.strip()
    # Full URL: https://github.com/username or http://github.com/username
    if re.match(r'https?://github\.com/[^/\s?#]+/?$', text, re.IGNORECASE):
        return True
    # Without protocol: github.com/username
    if re.match(r'github\.com/[^/\s?#]+/?$', text, re.IGNORECASE):
        return True
    return False


def extract_from_github_url(github_url: str) -> dict:
    """
    Extract candidate data directly from a GitHub profile URL.

    Strategy:
    1. Parse the username from the URL.
    2. Hit GitHub REST API for profile + top repos (no auth needed for public profiles).
    3. Map structured API response directly to CSV fields — zero LLM calls.
    4. Infer seniority heuristically from followers + public_repos count.

    Returns the same shape as extract_from_text() so the rest of the ingest
    pipeline is unchanged.
    """
    # Lazy import to avoid circular dependency (github_sourcing also imports guardrails)
    from ai.github_sourcing import _fetch_user_details, _fetch_user_repos

    # --- 1. Parse username ---------------------------------------------------
    raw = github_url.strip().rstrip("/")
    match = re.search(r'github\.com/([^/\s?#]+)', raw, re.IGNORECASE)
    if match:
        username = match.group(1)
    else:
        username = raw  # treat bare input as a username

    # --- 2. Fetch from GitHub API -------------------------------------------
    details = _fetch_user_details(username)
    if not details or details.get("message") == "Not Found":
        return {"error": f"GitHub profile '{username}' not found. Check the URL and try again."}

    repos = _fetch_user_repos(username, limit=10)

    # Collect programming languages from repos
    languages = list(dict.fromkeys(  # preserve insertion order, deduplicate
        r["language"] for r in repos if r.get("language")
    ))

    # --- 3. Build project_summary -------------------------------------------
    bio = (details.get("bio") or "").strip()
    top_repos_text = "; ".join(
        "{name} ({lang}, {stars}★)".format(
            name=r["name"],
            lang=r.get("language") or "?",
            stars=r.get("stars", 0),
        )
        for r in repos[:5]
        if r.get("name")
    )
    summary_parts = [p for p in [bio, f"Top repos: {top_repos_text}" if top_repos_text else ""] if p]
    project_summary = " | ".join(summary_parts)

    # --- 4. Heuristic seniority from public signals -------------------------
    followers = details.get("followers", 0)
    public_repos = details.get("public_repos", 0)
    if followers > 500 or public_repos > 60:
        seniority = "senior"
    elif followers > 100 or public_repos > 25:
        seniority = "mid"
    elif public_repos > 8:
        seniority = "junior"
    else:
        seniority = "intern"

    # Strip leading "@" from company field (GitHub convention)
    company = (details.get("company") or "").replace("@", "").strip()

    # --- 5. Return mapped dict ----------------------------------------------
    result = {
        "name":                details.get("name") or username,
        "seniority":           seniority,
        "years_of_experience": "",   # not determinable from GitHub alone
        "current_role":        company,
        "previous_jobs":       "",
        "degrees":             "",
        "location":            details.get("location") or "",
        "languages":           "",   # spoken languages — not on GitHub
        "technologies":        ", ".join(lang.lower() for lang in languages),
        "project_summary":     project_summary,
        "linkedin_url":        "",
        "email":               details.get("email") or "",
        "github_url":          f"https://github.com/{username}",
    }

    # Infer a proper role title from repos/technologies if we only have a
    # company name (or nothing at all) — GitHub doesn't expose job titles.
    inferred = infer_role_from_experience(result)
    if inferred:
        if company:
            result["current_role"] = f"{inferred} @ {company}"
        else:
            result["current_role"] = inferred
        print(f"[Ingestion] Inferred GitHub role: {result['current_role']}")

    return result



def check_duplicate(name: str, email: str = "", linkedin_url: str = "") -> dict | None:
    """
    Check if a candidate already exists in the talent pool.
    Returns the existing row if found, None otherwise.
    """
    if not CSV_PATH.exists():
        return None
    
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Match by name (case-insensitive)
            if row.get("name", "").strip().lower() == name.strip().lower():
                return row
            # Match by email
            if email and row.get("email", "").strip().lower() == email.strip().lower():
                return row
            # Match by LinkedIn URL
            if linkedin_url and row.get("linkedin_url", "").strip().lower() == linkedin_url.strip().lower():
                return row
    
    return None


def add_candidate_to_csv(candidate_data: dict) -> bool:
    """
    Write an approved candidate row to the CSV.
    Called after human-in-the-loop approval.
    """
    from datetime import datetime
    
    # Ensure data directory exists
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Default values for new candidates
    candidate_data.setdefault("status", "active")
    candidate_data.setdefault("outreach_status", "not_contacted")
    candidate_data.setdefault("outreach_date", "")
    candidate_data.setdefault("last_updated_at", datetime.now().strftime("%Y-%m-%d"))
    candidate_data.setdefault("github_url", "")
    
    # Read existing CSV (if exists)
    file_exists = CSV_PATH.exists()
    fieldnames = [
        "name", "seniority", "years_of_experience", "current_role",
        "previous_jobs", "degrees", "location", "languages",
        "technologies", "project_summary", "linkedin_url", "github_url",
        "email", "status", "outreach_status", "outreach_date", "last_updated_at"
    ]
    
    try:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            # Only write fields that exist in fieldnames
            row = {k: candidate_data.get(k, "") for k in fieldnames}
            writer.writerow(row)
        
        return True
    except Exception as e:
        print(f"Error writing to CSV: {e}")
        return False


def update_candidate_in_csv(name: str, updated_data: dict) -> bool:
    """
    Update an existing candidate's data in the CSV (for merge/refresh).
    """
    from datetime import datetime
    
    if not CSV_PATH.exists():
        return False
    
    rows = []
    updated = False
    
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("name", "").strip().lower() == name.strip().lower():
                # Merge: update only non-empty new fields
                for key, value in updated_data.items():
                    if value and key in row:
                        row[key] = value
                row["last_updated_at"] = datetime.now().strftime("%Y-%m-%d")
                updated = True
            rows.append(row)
    
    if updated:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    return updated
