"""
Deterministic weighted scorer for the shortlisting engine.

Replaces the LLM's subjective 0-100 numbers with an auditable formula:

    matchScore = 0.45 * skills
               + 0.20 * seniority
               + 0.15 * industry
               + 0.15 * location
               + 0.05 * status

Skill scoring (per required skill):
    exact match   → 1.0
    similar match → 0.8     (synonym or substring)
    no match      → 0.0
    skill_score   = Σ values / |required_skills|

The LLM is still used to **parse the JD** into structured requirements
(`required_skills`, `min_seniority`, `industry`, `location`, `remote_ok`) —
that step alone is too fuzzy for a regex. Everything after JD parsing is
pure Python so the result is reproducible and explainable.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ai.guardrails import get_system_guardrail_prompt, validate_json_output

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weights from the product spec (sum to 1.00)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "skills": 0.45,
    "seniority": 0.20,
    "industry": 0.15,
    "location": 0.15,
    "status": 0.05,
}

SKILL_MATCH_VALUES = {
    "exact": 1.0,
    "similar": 0.8,
    "none": 0.0,
}

# Canonical ordering for the seniority distance heuristic.
SENIORITY_ORDER = ["intern", "junior", "mid", "mid_to_senior", "senior", "lead"]

# Synonyms for the "similar match" tier. The map is intentionally small and
# focused on tech terms that show up in this pool; extend it as the pool grows.
SKILL_SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "ml": "machine-learning",
    "ai": "artificial-intelligence",
    "dl": "deep-learning",
    "k8s": "kubernetes",
    "fe": "frontend",
    "be": "backend",
    "node": "nodejs",
    "node.js": "nodejs",
    "tf": "tensorflow",
    "pt": "pytorch",
    "psql": "postgresql",
    "postgres": "postgresql",
    "react.js": "react",
    "vue.js": "vue",
    ".net": "dotnet",
    "c sharp": "csharp",
    "c#": "csharp",
    "c++": "cpp",
    "golang": "go",
}

# Keyword sets used to score industry/department fit without an explicit field.
INDUSTRY_KEYWORDS = {
    "fintech":     ["bank", "finance", "financial", "trading", "blockchain", "crypto", "payment", "fintech", "raiffeisen"],
    "healthcare":  ["health", "medical", "hospital", "pharma", "biotech", "clinic", "patient"],
    "automotive":  ["automotive", "vehicle", "tesla", "bmw", "ford", "car-manufacturing"],
    "ecommerce":   ["ecommerce", "e-commerce", "retail", "shop", "marketplace", "shopify"],
    "gaming":      ["game", "gamedev", "godot", "unity", "unreal", "gaming"],
    "ai":          ["ai", "ml", "machine-learning", "deep-learning", "neural", "llm", "huggingface", "laion"],
    "saas":        ["saas", "b2b", "platform", "subscription"],
    "media":       ["media", "publishing", "news", "content", "youtube", "tiktok"],
    "education":   ["education", "university", "school", "lingoda", "edtech", "teaching"],
    "consulting":  ["consulting", "advisory", "deloitte", "kpmg", "ey", "pwc"],
    "legal":       ["legal", "law", "compliance", "lawyer", "attorney"],
    "business-intelligence": ["business intelligence", "bi", "data analyst", "tableau", "powerbi", "looker", "dashboard", "analytics"],
    "data":        ["data", "analytics", "sql", "warehouse", "etl", "pipeline", "bigquery", "snowflake"],
    "hr":          ["hr", "human resources", "recruitment", "talent", "sourcing", "people", "acquisition"],
    "product":     ["product", "pm", "product management", "roadmap", "agile", "scrum", "owner"],
    "marketing":   ["marketing", "seo", "campaign", "growth", "content", "social media", "ads"],
}


# ---------------------------------------------------------------------------
# JD parsing (LLM)
# ---------------------------------------------------------------------------

_JD_PARSE_SYSTEM = get_system_guardrail_prompt() + """
You parse a free-form job description into structured requirements for a
scoring engine. Return a JSON object with EXACTLY these keys:

  "required_skills":   list of lowercase tech/tool/skill/domain strings (e.g. ["python", "powerbi", "recruiting", "agile"])
                       Include only skills explicitly named or strongly implied by the JD.
                       6-12 items max — focus on the actually-required ones.
  "min_seniority":     one of: "intern", "junior", "mid", "mid_to_senior", "senior", "lead"
                       Default to "mid" if not specified.
  "industry":          one of: "fintech", "healthcare", "automotive", "ecommerce", "gaming",
                       "ai", "saas", "media", "education", "consulting", "legal",
                       "business-intelligence", "data", "hr", "product", "marketing", "" (empty if none).
  "location":          city or country mentioned in JD (e.g. "Cluj-Napoca"). "" if none.
  "remote_ok":         true if the JD says remote/hybrid/anywhere, false otherwise.

Return only the JSON object, no prose.
{format_instructions}
"""


def parse_job_description(jd: str, llm) -> dict[str, Any]:
    """Use the LLM to extract structured requirements from a job description."""
    parser = JsonOutputParser()
    prompt = ChatPromptTemplate.from_messages([
        ("system", _JD_PARSE_SYSTEM),
        ("human", "Job description:\n\n{jd}"),
    ])
    chain = prompt | llm | parser
    try:
        result = chain.invoke({"jd": jd[:3000], "format_instructions": parser.get_format_instructions()})
        validated, ok = validate_json_output(result)
        if not ok or not isinstance(validated, dict):
            raise ValueError("Bad JSON")
        # Normalize
        validated["required_skills"] = [s.strip().lower() for s in (validated.get("required_skills") or []) if s]
        validated["min_seniority"] = (validated.get("min_seniority") or "mid").lower().strip()
        validated["industry"] = (validated.get("industry") or "").lower().strip()
        validated["location"] = (validated.get("location") or "").strip()
        validated["remote_ok"] = bool(validated.get("remote_ok"))
        return validated
    except Exception as e:
        logger.warning("JD parsing failed (%s) — falling back to keyword heuristic", e)
        return _fallback_jd_parse(jd)


def _fallback_jd_parse(jd: str) -> dict[str, Any]:
    """Best-effort regex parse if the LLM call fails."""
    lower = jd.lower()
    seniority = "mid"
    for level in ("lead", "senior", "mid_to_senior", "mid", "junior", "intern"):
        if level.replace("_", " ") in lower or level.replace("_", "-") in lower:
            seniority = level
            break
    return {
        "required_skills": [],
        "min_seniority": seniority,
        "industry": "",
        "location": "",
        "remote_ok": "remote" in lower or "hybrid" in lower,
    }


# ---------------------------------------------------------------------------
# Per-field scoring (deterministic 0..1)
# ---------------------------------------------------------------------------

def _canon_skill(s: str) -> str:
    s = s.strip().lower()
    return SKILL_SYNONYMS.get(s, s)


def _skill_match_type(required: str, candidate_skills: list[str]) -> str:
    """Return 'exact' / 'similar' / 'none' for one required skill."""
    req = _canon_skill(required)
    canon_candidates = [_canon_skill(s) for s in candidate_skills]

    if req in canon_candidates:
        return "exact"

    # Similar: substring in either direction (covers "react" vs "react-native")
    for s in canon_candidates:
        if not s:
            continue
        if req in s or s in req:
            return "similar"
    return "none"


def score_skills(required_skills: list[str], candidate_techs: str) -> tuple[float, list[dict]]:
    """Returns (score in 0..1, per-skill breakdown for UI)."""
    if not required_skills:
        return 1.0, []  # No requirement → don't penalize

    cand = [s.strip() for s in (candidate_techs or "").split(",") if s.strip()]
    matched_value = 0.0
    breakdown: list[dict] = []
    for req in required_skills:
        match = _skill_match_type(req, cand)
        value = SKILL_MATCH_VALUES[match]
        matched_value += value
        breakdown.append({"skill": req, "match": match, "value": value})

    return matched_value / len(required_skills), breakdown


def score_seniority(required: str, candidate_seniority: str) -> float:
    """Linear decay around the requested level (0.25 per step)."""
    if not required or not candidate_seniority:
        return 0.5
    req = required.lower().strip().replace(" ", "_").replace("-", "_")
    cand = candidate_seniority.lower().strip().replace(" ", "_").replace("-", "_")
    try:
        req_idx = SENIORITY_ORDER.index(req)
        cand_idx = SENIORITY_ORDER.index(cand)
    except ValueError:
        return 0.5
    return max(0.0, 1.0 - abs(req_idx - cand_idx) * 0.25)


def score_industry(required: str, candidate: dict) -> float:
    """Keyword-based industry fit. Returns 0..1."""
    if not required:
        return 0.5

    req_lower = required.lower().strip()
    keywords = INDUSTRY_KEYWORDS.get(req_lower, [req_lower])
    haystack = " ".join([
        candidate.get("current_role", ""),
        candidate.get("previous_jobs", ""),
        candidate.get("project_summary", ""),
        candidate.get("technologies", ""),
    ]).lower()

    hits = sum(1 for kw in keywords if kw and kw in haystack)
    if hits >= 2:
        return 1.0
    if hits == 1:
        return 0.7
    return 0.2


def score_location(required: str, candidate_location: str, remote_ok: bool) -> float:
    """Simple geographical-fit heuristic."""
    if remote_ok:
        return 1.0
    if not required or not candidate_location:
        return 0.5
    req_lower = required.lower()
    cand_lower = candidate_location.lower()
    if req_lower in cand_lower or cand_lower in req_lower:
        return 1.0
    # Same country fallback — works for Romania since most candidates live there.
    if any(country in cand_lower and country in req_lower for country in ("romania", "moldova", "germany", "uk")):
        return 0.6
    return 0.2


def score_status(candidate: dict) -> float:
    """Availability proxy: consent status + freshness of last_updated_at."""
    status = (candidate.get("status") or "").lower()
    if status == "active":
        base = 1.0
    elif status == "pending_consent":
        base = 0.6
    else:
        base = 0.3

    last_updated = candidate.get("last_updated_at", "")
    try:
        last = datetime.strptime(last_updated.strip(), "%Y-%m-%d")
        days = (datetime.now() - last).days
        if days > 365:
            base *= 0.6
        elif days > 180:
            base *= 0.8
    except (ValueError, AttributeError):
        pass
    return base


# ---------------------------------------------------------------------------
# Top-level scoring
# ---------------------------------------------------------------------------

def score_candidate(candidate: dict, requirements: dict) -> dict:
    """Compute the weighted total + every sub-score + breakdown.

    Returns a dict shaped for the existing CandidateCard component plus extra
    fields (`industryScore`, `statusScore`, `skill_breakdown`, `weights`) so
    the UI can render the formula.
    """
    skills, skill_breakdown = score_skills(
        requirements.get("required_skills", []),
        candidate.get("technologies", ""),
    )
    seniority = score_seniority(
        requirements.get("min_seniority", ""),
        candidate.get("seniority", ""),
    )
    industry = score_industry(
        requirements.get("industry", ""),
        candidate,
    )
    location = score_location(
        requirements.get("location", ""),
        candidate.get("location", ""),
        requirements.get("remote_ok", False),
    )
    status = score_status(candidate)

    total = (
        WEIGHTS["skills"] * skills
        + WEIGHTS["seniority"] * seniority
        + WEIGHTS["industry"] * industry
        + WEIGHTS["location"] * location
        + WEIGHTS["status"] * status
    )

    name = candidate.get("name", "")
    initials = "".join(part[:1] for part in name.split() if part)[:2].upper() or "?"
    match_score = round(total * 100)

    if match_score >= 80:
        rank = "Excellent"
        color = "purple"
    elif match_score >= 60:
        rank = "Good"
        color = "green"
    else:
        rank = "Fair"
        color = "blue"

    # Citation: the strongest skill hit + location/industry mention if any
    citation_parts = []
    matched_skills = [b["skill"] for b in skill_breakdown if b["match"] != "none"]
    if matched_skills:
        citation_parts.append(f"Skills: {', '.join(matched_skills[:5])}")
    if requirements.get("location") and location >= 0.6:
        citation_parts.append(f"Location: {candidate.get('location', '')}")
    if requirements.get("industry") and industry >= 0.7:
        citation_parts.append(f"Industry signal in {requirements['industry']}")
    citation = " | ".join(citation_parts) or "Semantic match from candidate profile"

    tags = [b["skill"] for b in skill_breakdown[:3]] or \
           [s.strip() for s in (candidate.get("technologies") or "").split(",")[:3] if s.strip()]

    return {
        "initials": initials,
        "name": name,
        "role": candidate.get("current_role") or candidate.get("seniority", ""),
        "matchScore": match_score,
        "matchRank": rank,
        "skillsScore": round(skills * 100),
        "expScore": round(seniority * 100),
        "industryScore": round(industry * 100),
        "locationScore": round(location * 100),
        "statusScore": round(status * 100),
        "tags": tags,
        "langs": candidate.get("languages", ""),
        "github_url": candidate.get("github_url", ""),
        "citation": citation,
        "colorTheme": color,
        "skill_breakdown": skill_breakdown,
        "weights": WEIGHTS,
        "requirements_used": requirements,
    }


def rank_candidates(candidates: list[dict], requirements: dict, top_n: int = 3) -> list[dict]:
    """Score every candidate and return the top N by matchScore."""
    scored = [score_candidate(c, requirements) for c in candidates]
    scored.sort(key=lambda x: x["matchScore"], reverse=True)
    return scored[:top_n]
