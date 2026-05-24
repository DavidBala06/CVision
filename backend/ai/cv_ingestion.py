"""
CV Ingestion — Module 1: Extract Agent.

LLM-driven extraction from CV PDF text or pasted LinkedIn text into the
structured CSV schema. The CSV I/O helpers live in `csv_store.py` so they
can be tested without LangChain installed.
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Re-export the CSV helpers so existing imports (main.py, pool_maintenance.py)
# keep working without a churn.
from ai.csv_store import (  # noqa: F401
    CSV_FIELDNAMES,
    add_candidate_to_csv,
    check_duplicate,
    update_candidate_in_csv,
)
from ai.guardrails import get_system_guardrail_prompt, validate_json_output
from ai.llm_provider import get_chat_llm

load_dotenv()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))

# CSV columns that the LLM must extract (subset of CSV_FIELDNAMES — admin
# fields like status / outreach_status are filled in by csv_store).
EXTRACTION_FIELDS = [
    "name", "seniority", "years_of_experience", "current_role",
    "previous_jobs", "degrees", "location", "languages",
    "technologies", "project_summary", "linkedin_url", "email",
]


def get_llm():
    """Centralized LLM access — switches provider via LLM_PROVIDER env var."""
    return get_chat_llm(temperature=0.01, max_tokens=2048)


def extract_from_text(raw_text: str) -> dict:
    """Extract structured candidate information from raw CV/LinkedIn text.

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

    # Larger CVs sometimes exceed 5000 chars; chunk-truncate but keep both ends
    # so contact info (usually at the top) and recent experience (often at the
    # bottom) both make it into the prompt.
    if len(raw_text) > 8000:
        truncated = raw_text[:5000] + "\n\n[...middle truncated...]\n\n" + raw_text[-3000:]
    else:
        truncated = raw_text

    try:
        result = chain.invoke({
            "text": truncated,
            "format_instructions": f"Return a JSON object with exactly these keys: {json.dumps(EXTRACTION_FIELDS)}",
        })

        validated, ok = validate_json_output(result)
        if not ok:
            return {"error": "LLM returned invalid format"}

        if isinstance(validated, dict):
            for field in EXTRACTION_FIELDS:
                if field not in validated:
                    validated[field] = ""
            return validated

        return {"error": "LLM returned invalid format"}

    except Exception as e:
        logger.exception("Extraction failed")
        return {"error": f"Extraction failed: {str(e)}"}
