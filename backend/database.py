"""
Database Module - SQLAlchemy ORM

Models: Candidate, HiringRequest, Application
Default: SQLite (data/linnify.db)
Switch to PostgreSQL: set DATABASE_URL=postgresql://user:pass@host/db
"""
import os
import csv
from pathlib import Path
from datetime import datetime, date

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, Date,
    DateTime, ForeignKey, Enum as SAEnum, event
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = f"sqlite:///{BASE_DIR / 'data' / 'linnify.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    seniority = Column(String(50), default="")
    years_of_experience = Column(String(20), default="")
    current_role = Column(String(300), default="")
    previous_jobs = Column(Text, default="")
    degrees = Column(Text, default="")
    location = Column(String(200), default="")
    languages = Column(String(300), default="")
    technologies = Column(Text, default="")
    project_summary = Column(Text, default="")
    linkedin_url = Column(String(500), default="")
    github_url = Column(String(500), default="")
    email = Column(String(200), default="")
    status = Column(String(50), default="pending_consent")
    outreach_status = Column(String(50), default="not_contacted")
    outreach_date = Column(String(20), default="")
    last_updated_at = Column(String(20), default="")

    applications = relationship("Application", back_populates="candidate")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name or "",
            "seniority": self.seniority or "",
            "years_of_experience": self.years_of_experience or "",
            "current_role": self.current_role or "",
            "previous_jobs": self.previous_jobs or "",
            "degrees": self.degrees or "",
            "location": self.location or "",
            "languages": self.languages or "",
            "technologies": self.technologies or "",
            "project_summary": self.project_summary or "",
            "linkedin_url": self.linkedin_url or "",
            "github_url": self.github_url or "",
            "email": self.email or "",
            "status": self.status or "",
            "outreach_status": self.outreach_status or "",
            "outreach_date": self.outreach_date or "",
            "last_updated_at": self.last_updated_at or "",
        }


class HiringRequest(Base):
    __tablename__ = "hiring_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    location = Column(String(200), default="")
    hiring_manager = Column(String(200), default="")
    open_date = Column(String(20), default="")
    end_date = Column(String(20), default="")  # optional / nullable
    status = Column(String(50), default="open")  # draft, open, closed, on_hold

    applications = relationship("Application", back_populates="hiring_request")

    def to_dict(self):
        apps = self.applications or []
        in_progress_steps = {"screening", "interview", "offer"}
        return {
            "id": self.id,
            "job_title": self.job_title or "",
            "description": self.description or "",
            "location": self.location or "",
            "hiring_manager": self.hiring_manager or "",
            "open_date": self.open_date or "",
            "end_date": self.end_date or "",
            "status": self.status or "open",
            "total_applicants": len(apps),
            "in_progress": sum(1 for a in apps if (a.step or "") in in_progress_steps),
        }


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hiring_request_id = Column(Integer, ForeignKey("hiring_requests.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    candidate_name = Column(String(200), nullable=False)
    source = Column(String(100), default="")  # referral, internal, linnify, linkedin, github
    applied_date = Column(String(20), default="")
    step = Column(String(50), default="applied")  # applied, screening, interview, offer, hired, rejected
    category = Column(String(20), default="applicant")  # applicant or lead
    notes = Column(Text, default="")

    hiring_request = relationship("HiringRequest", back_populates="applications")
    candidate = relationship("Candidate", back_populates="applications")

    def to_dict(self):
        result = {
            "id": self.id,
            "hiring_request_id": self.hiring_request_id,
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name or "",
            "source": self.source or "",
            "applied_date": self.applied_date or "",
            "step": self.step or "applied",
            "category": self.category or "applicant",
            "notes": self.notes or "",
        }
        # Include candidate details if loaded
        if self.candidate:
            c = self.candidate
            result["current_role"] = c.current_role or ""
            result["years_of_experience"] = c.years_of_experience or ""
            result["degrees"] = c.degrees or ""
            result["location"] = c.location or ""
        return result


# ---------------------------------------------------------------------------
# Init + Seed
# ---------------------------------------------------------------------------

CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))


def init_db():
    """Create all tables and migrate CSV data if candidates table is empty."""
    Base.metadata.create_all(engine)

    session = SessionLocal()
    try:
        count = session.query(Candidate).count()
        if count == 0 and CSV_PATH.exists():
            print("[DB] Migrating candidates from CSV to database...")
            _migrate_csv_to_db(session)

        # Seed demo hiring requests if empty
        hr_count = session.query(HiringRequest).count()
        if hr_count == 0:
            _seed_hiring_requests(session)

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[DB] Init error: {e}")
        raise
    finally:
        session.close()


def _migrate_csv_to_db(session):
    """Import talent_pool.csv rows into the candidates table."""
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            candidate = Candidate(
                name=row.get("name", ""),
                seniority=row.get("seniority", ""),
                years_of_experience=row.get("years_of_experience", ""),
                current_role=row.get("current_role", ""),
                previous_jobs=row.get("previous_jobs", ""),
                degrees=row.get("degrees", ""),
                location=row.get("location", ""),
                languages=row.get("languages", ""),
                technologies=row.get("technologies", ""),
                project_summary=row.get("project_summary", ""),
                linkedin_url=row.get("linkedin_url", ""),
                github_url=row.get("github_url", ""),
                email=row.get("email", ""),
                status=row.get("status", "pending_consent"),
                outreach_status=row.get("outreach_status", "not_contacted"),
                outreach_date=row.get("outreach_date", ""),
                last_updated_at=row.get("last_updated_at", ""),
            )
            session.add(candidate)
            count += 1
        print(f"[DB] Migrated {count} candidates from CSV.")


def _seed_hiring_requests(session):
    """Seed demo hiring requests for the demo."""
    today = datetime.now().strftime("%Y-%m-%d")
    jobs = [
        HiringRequest(
            job_title="Senior Python Developer",
            description="We are looking for a Senior Python Developer to join our backend team. "
                        "Requirements: 5+ years Python, FastAPI/Django, PostgreSQL, Docker. "
                        "Nice to have: ML/AI experience, cloud infrastructure (AWS/GCP).",
            location="Cluj-Napoca",
            hiring_manager="Elena Popescu",
            open_date=today,
            status="open",
        ),
        HiringRequest(
            job_title="Frontend Engineer (React)",
            description="Join our product team as a Frontend Engineer. "
                        "Requirements: 3+ years React/TypeScript, state management, responsive design. "
                        "Nice to have: Next.js, design system experience.",
            location="Remote (Romania)",
            hiring_manager="Andrei Marinescu",
            open_date=today,
            status="open",
        ),
        HiringRequest(
            job_title="DevOps Engineer",
            description="We need a DevOps Engineer to manage our cloud infrastructure. "
                        "Requirements: Kubernetes, CI/CD pipelines, Terraform, AWS or GCP. "
                        "Experience with monitoring (Prometheus, Grafana) is a plus.",
            location="Bucharest",
            hiring_manager="Elena Popescu",
            open_date=today,
            status="open",
        ),
        HiringRequest(
            job_title="Product Manager - Cybersecurity",
            description="Looking for a Product Manager with cybersecurity domain expertise. "
                        "Requirements: 3+ years PM experience, Agile/Scrum, stakeholder management. "
                        "Domain knowledge in threat detection or compliance preferred.",
            location="Cluj-Napoca",
            hiring_manager="Mihai Ionescu",
            open_date=today,
            status="draft",
        ),
        HiringRequest(
            job_title="Junior Full-Stack Developer",
            description="Entry-level Full-Stack Developer position. "
                        "Requirements: JavaScript/TypeScript, React or Vue, Node.js basics. "
                        "Great opportunity for recent graduates with strong fundamentals.",
            location="Timisoara",
            hiring_manager="Andrei Marinescu",
            open_date=today,
            status="open",
        ),
    ]
    for job in jobs:
        session.add(job)

    print(f"[DB] Seeded {len(jobs)} demo hiring requests.")


def get_session():
    """Get a new database session."""
    return SessionLocal()
