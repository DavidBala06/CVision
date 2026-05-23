"""
CV Ingestion Module 

Handles:
Manual CV/LinkedIn extraction → structured JSON mapped to CSV columns
All required fields (name, seniority, years_exp, etc.)


Also performs dedup checking against existing talent pool.
"""
import os
import csv
import json
from pathlib import Path
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

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
            return result
        
        return {"error": "LLM returned invalid format"}
        
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}


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
