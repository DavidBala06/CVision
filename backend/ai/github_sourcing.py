"""
GitHub Sourcing Module

Replaces LinkedIn sourcing. Uses the GitHub Search API to find
developer candidates matching job criteria.

Two modes:
  - search_by_criteria: Natural language job description → GitHub user search
  - search_by_profile: GitHub profile URL → find similar developers
"""
import os
import re
import requests
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ai.guardrails import get_system_guardrail_prompt

load_dotenv()

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Optional, increases rate limit


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def _get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=1024,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )


def _fetch_user_details(username: str) -> dict:
    """Fetch detailed GitHub user profile."""
    try:
        resp = requests.get(f"{GITHUB_API}/users/{username}", headers=_github_headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def _fetch_user_repos(username: str, limit: int = 5) -> list[dict]:
    """Fetch top repos (by stars) for a user."""
    try:
        resp = requests.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=_github_headers(),
            params={"sort": "stars", "direction": "desc", "per_page": limit},
            timeout=10,
        )
        if resp.status_code == 200:
            repos = resp.json()
            return [
                {
                    "name": r.get("name", ""),
                    "description": (r.get("description") or "")[:120],
                    "stars": r.get("stargazers_count", 0),
                    "language": r.get("language", ""),
                    "url": r.get("html_url", ""),
                    "forks": r.get("forks_count", 0),
                }
                for r in repos[:limit]
            ]
    except Exception:
        pass
    return []


def _enrich_user(user: dict) -> dict:
    """Take a GitHub Search API user result and enrich with profile + repos."""
    username = user.get("login", "")
    details = _fetch_user_details(username)
    repos = _fetch_user_repos(username, limit=5)

    # Collect languages from repos
    languages = list({r["language"] for r in repos if r.get("language")})

    return {
        "username": username,
        "name": details.get("name") or username,
        "avatar_url": user.get("avatar_url", ""),
        "profile_url": f"https://github.com/{username}",
        "bio": details.get("bio") or "",
        "location": details.get("location") or "",
        "company": details.get("company") or "",
        "public_repos": details.get("public_repos", 0),
        "followers": details.get("followers", 0),
        "languages": languages,
        "top_repos": repos,
        "hireable": details.get("hireable") or False,
    }


def search_by_criteria(job_description: str) -> dict:
    """
    Given a natural-language job description, use the LLM to extract
    GitHub search keywords, then query the GitHub Search API.
    """
    llm = _get_llm()
    parser = JsonOutputParser()

    # Step 1: LLM extracts search parameters
    extract_prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are a GitHub talent sourcing specialist. Given a job description,
generate an optimized GitHub user search query.

Return a JSON object with:
- "search_query": GitHub Search API query string (e.g., "language:python location:Romania fullname:engineer")
  Use GitHub qualifiers: language:X, location:X, followers:>N, repos:>N
- "keywords": plain text keywords to also try (e.g., "machine learning python")
- "languages": list of programming languages relevant to the role
- "location_hint": location if mentioned, else ""
- "experience_level": "Junior", "Mid", or "Senior"
- "sourcing_tips": 2-3 tips for evaluating GitHub profiles for this role

{format_instructions}
"""),
        ("human", "Generate a GitHub search strategy for this job:\n\n{job_description}")
    ])

    try:
        extract_chain = extract_prompt | llm | parser
        strategy = extract_chain.invoke({
            "job_description": job_description[:2000],
            "format_instructions": parser.get_format_instructions(),
        })
    except Exception as e:
        return {"error": f"Failed to generate search strategy: {str(e)}"}

    # Step 2: Query GitHub Search API
    search_query = strategy.get("search_query", strategy.get("keywords", job_description[:100]))
    try:
        resp = requests.get(
            f"{GITHUB_API}/search/users",
            headers=_github_headers(),
            params={"q": search_query, "per_page": 8},
            timeout=15,
        )

        if resp.status_code != 200:
            # Fallback: try with just keywords
            fallback_q = " ".join(strategy.get("languages", [])[:2])
            location = strategy.get("location_hint", "")
            if location:
                fallback_q += f" location:{location}"
            resp = requests.get(
                f"{GITHUB_API}/search/users",
                headers=_github_headers(),
                params={"q": fallback_q, "per_page": 8},
                timeout=15,
            )

        if resp.status_code == 200:
            raw_users = resp.json().get("items", [])[:6]
            profiles = [_enrich_user(u) for u in raw_users]
        else:
            profiles = []

    except Exception as e:
        profiles = []
        strategy["api_error"] = str(e)

    return {
        "search_strategy": strategy,
        "profiles": profiles,
        "total_found": len(profiles),
    }


def search_by_profile(github_input: str) -> dict:
    """
    Given a GitHub username or profile URL, analyze that developer
    and find similar profiles.
    """
    # Extract username from URL or use directly
    username = github_input.strip().rstrip("/")
    match = re.search(r"github\.com/([^/\s?]+)", username)
    if match:
        username = match.group(1)

    # Fetch the source profile
    source = _fetch_user_details(username)
    if not source:
        return {"error": f"Could not find GitHub user: {username}"}

    source_repos = _fetch_user_repos(username, limit=8)
    source_languages = list({r["language"] for r in source_repos if r.get("language")})

    # Use LLM to generate a "find similar" search strategy
    llm = _get_llm()
    parser = JsonOutputParser()

    profile_text = f"""
Username: {username}
Name: {source.get('name', '')}
Bio: {source.get('bio', '')}
Location: {source.get('location', '')}
Company: {source.get('company', '')}
Languages: {', '.join(source_languages)}
Top repos: {', '.join(r['name'] + ' (' + str(r['stars']) + '★, ' + (r['language'] or '?') + ')' for r in source_repos[:5])}
Followers: {source.get('followers', 0)}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are a GitHub talent sourcing specialist. Given a developer's GitHub profile,
generate a search strategy to find similar developers.

Return a JSON object with:
- "profile_summary": 1-sentence summary of this developer
- "key_traits": list of 5 defining technical traits
- "search_query": GitHub Search API query to find similar devs
- "alternative_search": a second GitHub search query variation
- "technologies": list of main technologies this dev uses
- "similar_titles": list of 3-5 job titles for similar devs
- "sourcing_tips": 2-3 tips for finding this type of developer

{format_instructions}
"""),
        ("human", "Find similar developers to this GitHub profile:\n\n{profile_text}")
    ])

    try:
        chain = prompt | llm | parser
        strategy = chain.invoke({
            "profile_text": profile_text,
            "format_instructions": parser.get_format_instructions(),
        })
    except Exception as e:
        return {"error": f"Profile analysis failed: {str(e)}"}

    # Search for similar profiles
    search_q = strategy.get("search_query", " ".join(source_languages[:2]))
    try:
        resp = requests.get(
            f"{GITHUB_API}/search/users",
            headers=_github_headers(),
            params={"q": search_q, "per_page": 8},
            timeout=15,
        )
        if resp.status_code == 200:
            raw_users = resp.json().get("items", [])
            # Filter out the source user
            raw_users = [u for u in raw_users if u.get("login", "").lower() != username.lower()][:6]
            profiles = [_enrich_user(u) for u in raw_users]
        else:
            profiles = []
    except Exception:
        profiles = []

    return {
        "source_profile": {
            "username": username,
            "name": source.get("name") or username,
            "avatar_url": source.get("avatar_url", ""),
            "bio": source.get("bio", ""),
            "location": source.get("location", ""),
            "languages": source_languages,
            "top_repos": source_repos[:5],
        },
        "search_strategy": strategy,
        "similar_profiles": profiles,
        "total_found": len(profiles),
    }
