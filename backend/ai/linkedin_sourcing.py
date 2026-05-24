"""
LinkedIn Sourcing Module 

Handles:
Candidate sourcing by role — generate LinkedIn search queries
Candidate sourcing by profile — find similar profiles

We are not scraping LinkedIn, it s against the policy
Instead, we generate optimized search queries/URLs for the HR user.
"""
import os
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ai.guardrails import get_system_guardrail_prompt
from ai.llm_provider import get_chat_llm

load_dotenv()


def get_llm():
    return get_chat_llm(temperature=0.3, max_tokens=1024)


def search_by_role(job_description: str) -> dict:
    
    # Generate optimized LinkedIn search query based on job role.
    # Returns structured search parameters and clickable Search URL
    
    llm = get_llm()
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are a LinkedIn sourcing specialist. Given a job description, generate an optimized
LinkedIn search strategy.

Return a JSON object with:
- "search_keywords": the main search query string (e.g., "Python Developer Machine Learning")
- "title_filter": suggested job title filter (e.g., "Software Engineer")
- "skills_filter": list of 3-5 key skills to filter by
- "location_filter": suggested location if mentioned
- "experience_level": "Entry", "Mid-Senior", or "Senior"
- "linkedin_search_url": a constructed LinkedIn search URL using the keywords
  Format: https://www.linkedin.com/search/results/people/?keywords=ENCODED_KEYWORDS
- "boolean_query": an advanced Boolean search string for LinkedIn
  (e.g., '("Python" OR "Django") AND ("Machine Learning" OR "AI") AND "Senior"')
- "sourcing_tips": 2-3 practical tips for finding this type of candidate

{format_instructions}
"""),
        ("human", "Generate a LinkedIn search strategy for this job:\n\n{job_description}")
    ])

    chain = prompt | llm | parser

    try:
        result = chain.invoke({
            "job_description": job_description[:2000],
            "format_instructions": parser.get_format_instructions()
        })
        return result if isinstance(result, dict) else {"error": "Invalid LLM response"}
    except Exception as e:
        return {"error": f"Search generation failed: {str(e)}"}


def search_by_profile(profile_text: str) -> dict:
    
    # Given a LinkedIn profile, find similar profiles.
    # Analyzes the profile and generates a "find similar" search strategy.
    
    llm = get_llm()
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are a LinkedIn sourcing specialist. Given a candidate's LinkedIn profile or URL,
analyze their key traits and generate a search strategy to find similar professionals.

Return a JSON object with:
- "profile_summary": brief 1-sentence summary of the source profile
- "key_traits": list of 5 defining traits (skills, industry, role type)
- "search_keywords": optimized LinkedIn search query for similar profiles
- "linkedin_search_url": constructed LinkedIn search URL
  Format: https://www.linkedin.com/search/results/people/?keywords=ENCODED_KEYWORDS
- "boolean_query": advanced Boolean search string for finding similar people
- "alternative_titles": list of 3-5 job titles similar people might have
- "companies_to_target": list of 3-5 companies where similar people might work
- "sourcing_tips": 2-3 tips for finding this type of professional

{format_instructions}
"""),
        ("human", "Analyze this profile and generate a 'find similar' search strategy:\n\n{profile_text}")
    ])

    chain = prompt | llm | parser

    try:
        result = chain.invoke({
            "profile_text": profile_text[:3000],
            "format_instructions": parser.get_format_instructions()
        })
        return result if isinstance(result, dict) else {"error": "Invalid LLM response"}
    except Exception as e:
        return {"error": f"Profile analysis failed: {str(e)}"}
