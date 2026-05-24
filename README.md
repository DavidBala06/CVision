# TalentAI by CVision

An intelligent Recruitment Assistant that helps HR teams identify the best-fit candidates faster, smarter, and more accurately than traditional ATS systems. Built for the Linnify AI Talent Pool Manager challenge.

## Core Architecture & Pivot
Throughout the buildathon, we successfully pivoted our architecture to meet all core challenge requirements while avoiding common AI pitfalls:
1. **Deterministic Scoring Engine:** We removed subjective "black-box" LLM candidate ranking. The LLM is now strictly used for **Job Description Parsing**. The actual ranking is done via a transparent, auditable Python weighted formula (45% Skills, 20% Seniority, 15% Industry, etc.), ensuring exact, reproducible results with zero hallucinated candidate matches.
2. **CSV Single Source of Truth:** We dropped the experimental Obsidian/Chroma vector databases in favor of a robust, structured `talent_pool.csv` database.
3. **GitHub Sourcing Integration:** Since LinkedIn scraping heavily restricts automated tooling, we pivoted to the **GitHub Search API** for deep developer insights.

## Features

### 1. Upload CV & Data Ingestion (Human-in-the-Loop)
- **AI Extraction (NER):** Paste a GitHub URL or upload a CV. The AI extracts structured fields (Name, Seniority, Tech Stack, Education).
- **Conflict Resolution:** If you upload a candidate who already exists, the system flags them as a duplicate and dynamically allows you to **Approve & Merge** the new data into their existing profile without creating duplicates.
- **Side-by-Side Review:** An embedded PDF viewer allows HR to cross-reference the original CV before approving AI data.

### 2. Intelligent Shortlisting
- **RAG-Powered Job Parsing:** Paste any unstructured job description. The AI extracts the required skills, industry, and seniority.
- **Transparent Match Breakdown:** Every shortlisted candidate displays a detailed breakdown of exactly why they matched, down to which specific skills were an exact match vs a synonym match.
- **Direct GitHub Access:** Candidate cards link directly to GitHub profiles for immediate technical evaluation.

### 3. Automated Outreach
- **Context-Aware Email Drafting:** Select a shortlisted candidate, and the AI automatically generates a highly personalized outreach email based on both the Job Description and the candidate's specific background.
- **Outreach Tracking:** Mark emails as sent and track the outreach funnel (Not Contacted -> Email Sent -> Replied -> No Reply).

### 4. Talent Pool Maintenance
- **Automated Stale Detection:** The system automatically flags candidates whose profiles haven't been updated in over 3 months.
- **One-Click Bulk Refresh:** Click "Refresh Stale" on the dashboard to automatically iterate through outdated profiles, ping the GitHub API for their latest repos/languages, and intelligently merge the fresh data into the CSV.

### 5. Metrics & GDPR Compliance
- A dedicated metrics dashboard tracking pool health, seniority/location distributions, and outreach funnels.
- **100% Local Data:** All candidate data is securely stored in a local CSV. No external vector databases or cloud storage APIs are used for data retention.

## Tech Stack
- **Backend:** Python 3.12, FastAPI, LangChain, Groq API (llama-3.3-70b-versatile)
- **Frontend:** React, TypeScript, Vite, CSS Flex/Grid
- **Data:** CSV-backed structured storage

## How to Run Locally

### 1. Backend (FastAPI)
Navigate to the `backend` folder, install requirements, and run Uvicorn:
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```
*Make sure to add your `GROQ_API_KEY` to `backend/.env`.*

### 2. Frontend (Vite + React)
In a separate terminal, navigate to the `frontend` folder:
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.
