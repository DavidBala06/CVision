"""
Outreach Agent

Handles:
Personalized email drafts (candidate + job -> email)
Progress monitoring + follow-up drafts
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ai.guardrails import get_system_guardrail_prompt

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.4,  # A bit more creative for emails
        max_tokens=1024,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )


def generate_email_draft(candidate: dict, job_description: str) -> str:
    """Generate a personalized outreach email."""
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are a professional HR recruiter writing personalized outreach emails.

RULES:
1. Be warm, professional, and concise (under 200 words).
2. Reference the candidate's SPECIFIC skills and experience from their profile.
3. Clearly describe the job opportunity.
4. Include a clear call-to-action (schedule a call, reply with interest).
5. Do NOT include fake information. Only reference what's in the candidate profile.
6. Write in English unless the candidate's languages suggest otherwise.
7. Do NOT include email headers (To, From, Subject) -- just the body.
"""),
        ("human", """CANDIDATE PROFILE:
Name: {name}
Current Role: {current_role}
Technologies: {technologies}
Experience: {years_of_experience} years
Location: {location}
Seniority: {seniority}

JOB OPPORTUNITY:
{job_description}

Write a personalized outreach email to this candidate about this job opportunity.""")
    ])

    chain = prompt | llm | StrOutputParser()

    try:
        result = chain.invoke({
            "name": candidate.get("name", ""),
            "current_role": candidate.get("current_role", ""),
            "technologies": candidate.get("technologies", ""),
            "years_of_experience": candidate.get("years_of_experience", ""),
            "location": candidate.get("location", ""),
            "seniority": candidate.get("seniority", ""),
            "job_description": job_description,
        })
        return result
    except Exception as e:
        return f"Error generating email: {str(e)}"


def generate_followup_draft(candidate: dict, original_email: str = "", days_since: int = 7) -> str:
    """Generate follow-up email for non-replies."""
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are a professional HR recruiter writing a follow-up email.

RULES:
1. Be polite and not pushy.
2. Reference the original outreach briefly.
3. Add a new angle or additional value proposition.
4. Keep it short (under 100 words).
5. Include a clear but gentle call-to-action.
"""),
        ("human", """CANDIDATE: {name} ({current_role})
DAYS SINCE FIRST EMAIL: {days_since}

Write a short, friendly follow-up email to this candidate who hasn't replied.""")
    ])

    chain = prompt | llm | StrOutputParser()

    try:
        return chain.invoke({
            "name": candidate.get("name", ""),
            "current_role": candidate.get("current_role", ""),
            "days_since": str(days_since),
        })
    except Exception as e:
        return f"Error generating follow-up: {str(e)}"


def update_outreach_status(candidate_name: str, status: str) -> bool:
    """Update a candidate's outreach status in the database."""
    from database import get_session, Candidate

    valid_statuses = ["not_contacted", "email_sent", "replied", "no_reply", "interested", "declined"]
    if status not in valid_statuses:
        return False

    session = get_session()
    try:
        candidate = session.query(Candidate).filter(
            Candidate.name.ilike(candidate_name.strip())
        ).first()
        if not candidate:
            return False

        candidate.outreach_status = status
        if status == "email_sent":
            candidate.outreach_date = datetime.now().strftime("%Y-%m-%d")
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error updating outreach status: {e}")
        return False
    finally:
        session.close()


def get_outreach_dashboard() -> dict:
    """Get outreach progress monitoring data."""
    from database import get_session, Candidate

    session = get_session()
    try:
        candidates_list = []
        summary = {"not_contacted": 0, "email_sent": 0, "replied": 0, "no_reply": 0, "interested": 0, "declined": 0}

        all_candidates = session.query(Candidate).all()
        for c in all_candidates:
            outreach_status = c.outreach_status or "not_contacted"
            outreach_date = c.outreach_date or ""

            summary[outreach_status] = summary.get(outreach_status, 0) + 1

            needs_followup = False
            if outreach_status == "email_sent" and outreach_date:
                try:
                    sent_date = datetime.strptime(outreach_date.strip(), "%Y-%m-%d")
                    if (datetime.now() - sent_date).days >= 7:
                        needs_followup = True
                except ValueError:
                    pass

            if outreach_status != "not_contacted":
                candidates_list.append({
                    "name": c.name or "",
                    "current_role": c.current_role or "",
                    "email": c.email or "",
                    "outreach_status": outreach_status,
                    "outreach_date": outreach_date,
                    "needs_followup": needs_followup,
                })

        return {"candidates": candidates_list, "summary": summary}
    finally:
        session.close()
