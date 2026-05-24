# CVision — TalentAI Agent

AI Recruitment Assistant that grows and maintains a talent pool, communicates
opportunities to selected candidates, and identifies the best-fit candidates —
with a human in the loop at every state change.

Built for the **Linnify "AI Talent Pool Manager"** challenge.

---

## What's inside

```
CVision/
├── backend/
│   ├── ai/
│   │   ├── RAG_engine.py        # Persistent Chroma + LLM-agnostic retriever chain
│   │   ├── cv_ingestion.py      # PDF / pasted text → structured fields (HITL approval)
│   │   ├── csv_store.py         # Pure CSV I/O (no LLM deps, easy to test)
│   │   ├── pool_maintenance.py  # Stale detection + self-refresh + intelligent merge
│   │   ├── outreach_agent.py    # Email + follow-up DRAFTS (never auto-sent)
│   │   ├── linkedin_sourcing.py # By-role / by-profile search strategies
│   │   ├── guardrails.py        # Prompt-injection filter + output validation
│   │   ├── llm_provider.py      # Groq / Mistral EU / Ollama abstraction
│   │   ├── audit_log.py         # Append-only JSONL of every action
│   │   └── pii.py               # Email masking for the dashboard endpoint
│   ├── evals/
│   │   ├── ground_truth.json    # 12 HR-style cases with expected matches
│   │   ├── evaluator.py         # precision@k / recall@k / MRR / leak-rate
│   │   └── run_eval.py          # `python -m evals.run_eval`
│   ├── tests/                   # pytest suite for guardrails, PII, eval, audit, dedup
│   ├── scraper/parser.py        # PDF → text helper
│   ├── data/talent_pool.csv     # The talent pool (single source of truth)
│   └── main.py                  # FastAPI app — 15 endpoints
├── frontend/
│   └── src/
│       ├── App.tsx
│       └── components/          # Dashboard, Shortlist, Upload, Outreach,
│                                  LinkedInSearch, Metrics, Sidebar, ChatArea
├── .env.example
├── requirements.txt
└── README.md
```

The talent pool is stored as a plain CSV (`backend/data/talent_pool.csv`).
That is the single source of truth — there is no external database or vault
behind it. New candidates are added through the **Upload CV** flow.

---

## Mapping to the Linnify challenge

| Module | Requirement | Endpoint(s) | Implementation |
|---|---|---|---|
| 1a | Manual CV/LinkedIn extraction | `POST /api/ingest`, `POST /api/ingest/approve` | PDF or pasted text → LLM extraction → HITL review form → CSV write |
| 1b | All 10 required fields | (CSV schema) | name, seniority, years_of_experience, current_role, previous_jobs, degrees, location, languages, technologies, project_summary |
| 1c | Automatic extraction (nice-to-have) | same | LLM-based NER (more flexible than classic NER) |
| 2a | Bulk refresh | `POST /api/refresh/update` | CSV-only self-refresh: normalizes tech list + seniority + bumps timestamp. *No autopull from LinkedIn — see "Refresh limitations" below.* |
| 2b | Auto-update detection | `GET /api/refresh/stale` | Flags candidates older than 3 months |
| 2c | Manual update / merge | `POST /api/refresh/merge` | HR pastes fresh CV/LinkedIn → dedup by name/email/LinkedIn → LLM intelligent_merge with deterministic fallback |
| 3a | Email drafts | `POST /api/draft-email` | Personalized draft using candidate profile + job description |
| 3b | Progress monitoring + follow-up | `GET /POST /api/outreach-status`, `POST /api/draft-followup` | Status tracking + 7-day follow-up flag |
| 4a | Shortlisting | `POST /api/match` | RAG with persistent Chroma + chat LLM + output validation |
| 4b | LinkedIn sourcing (nice-to-have) | `POST /api/linkedin-search` | Generates queries/URLs/Boolean strings — does NOT scrape (GDPR-safe) |
| Constraint: Compliance / GDPR | | `GET /api/provider` | `LLM_PROVIDER` toggles Groq (US) / Mistral (EU) / Ollama (local) with a UI badge |
| Constraint: Security | | guardrails | Regex + homoglyph/whitespace normalization, JSON output validation, sensitive-field stripping |
| Constraint: Human in the Loop | | every state change | Ingest, merge, refresh, outreach all require human action; PII contact reveal requires explicit endpoint call |
| Constraint: Success metrics (LangChain eval) | | `POST /api/evaluate`, `GET /api/metrics` | Real precision@k / recall@k / MRR / hit-rate / leak-rate against `evals/ground_truth.json` |
| Governance | | `GET /api/audit` | Append-only JSONL log of every action |

---

## Refresh limitations (intentional)

The Linnify brief mentions "automatically pulling their latest LinkedIn data".
This build deliberately does **not** scrape LinkedIn:

  - Scraping LinkedIn violates their Terms of Service and exposes the org to
    legal risk.
  - The official LinkedIn API requires a partner agreement, paid access, and
    GDPR data-processing contracts — out of scope for the hackathon.

Instead we provide two **honest** refresh paths:

  1. **Self-refresh** (`POST /api/refresh/update`): re-normalizes the
     candidate's existing fields (dedup + sort technologies, canonicalize
     seniority) and bumps `last_updated_at`. Useful for data hygiene; does
     not invent new information.
  2. **Manual merge** (`POST /api/refresh/merge`): the HR user pastes fresh
     CV / LinkedIn text into the form, the LLM extracts the fields, and the
     `intelligent_merge` chain reconciles them with the existing row.

When a paid LinkedIn integration is later added, only the data-source step
needs to change — the merge & vector-store logic stays the same.

---

## Run locally

### 1. Install backend deps
```powershell
cd CVision
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Configure environment
```powershell
copy .env.example .env
# Edit .env — pick LLM_PROVIDER and fill the matching API key
```

Set `LLM_PROVIDER=mistral` (EEA) or `LLM_PROVIDER=ollama` (fully local) for
GDPR-friendly processing. `LLM_PROVIDER=groq` is the fastest but US-hosted —
the UI will show a warning badge while it's active.

### 3. Start the backend
```powershell
cd backend
python main.py
# → http://127.0.0.1:8000
```

On first boot the backend reads `data/talent_pool.csv`, embeds the rows, and
persists the Chroma index to `chroma_csv_storage/`. Subsequent boots reuse
the index and only add documents that aren't already there.

### 4. Start the frontend
```powershell
cd frontend
npm install
npm run dev
# → http://127.0.0.1:5173
```

---

## How shortlisting scores are computed

There are **two separate scoring systems** in this build — don't confuse them.

### A) The "matchScore / skillsScore / expScore / locationScore" on candidate cards

These come from the **LLM**, not from a math formula. The shortlisting chain
in `ai/RAG_engine.py` works like this:

1. The HR query (e.g. "Senior Python ML engineer in Cluj") is sanitized
   through `guardrails.sanitize_input`.
2. HuggingFace `all-MiniLM-L6-v2` embeds the query and Chroma returns the
   **top-5** candidates by cosine similarity over the candidate profile text.
3. Those 5 candidates are formatted into a context block and passed to the
   chat LLM with a strict-grounding prompt that requires:
     - `matchScore` — overall fit, 0–100 integer
     - `skillsScore` — tech-stack overlap, 0–100
     - `expScore` — seniority/years-of-experience fit, 0–100
     - `locationScore` — location proximity / remote-friendliness, 0–100
     - `matchRank` — "Excellent" / "Good" / "Fair" qualitative label
     - `citation` — exact snippet from the candidate text proving the match
     - `tags`, `langs`, `linkedin_url`, `colorTheme`
4. The LLM picks up to **3** candidates from the 5 and assigns each one its
   scores. The prompt forbids inventing data and requires a citation.
5. The output passes through `validate_json_output` which:
     - strips any sensitive fields the LLM might have leaked,
     - enforces the JSON schema (all required keys present),
     - returns `[]` for anything malformed (safe default).

These scores are **subjective** — the LLM's judgment under tight constraints.
They are NOT a deterministic formula. That's why we need system (B) below to
measure whether the LLM is actually doing a good job.

### B) The eval metrics in the Metrics tab (precision@k / recall@k / MRR / accuracy)

These are computed **algorithmically** in `evals/evaluator.py`, against the
12 HR-style test cases in `evals/ground_truth.json`. For each test case we
have:

```json
{
  "query": "Senior Python ML engineer based in Cluj-Napoca",
  "expected_candidates": ["Alex R.", "David Bala"],
  "must_not_match": ["Alex Morega", "Roland Leth"]
}
```

We feed the query through the same shortlisting chain, take the top-k
candidates the LLM returned, and compute:

| Metric | Definition | What it measures |
|---|---|---|
| **Precision@k** | `\|hits in top-k\| / k` | Of the candidates the LLM returned, how many were actually relevant? |
| **Recall@k** | `\|hits in top-k\| / \|expected\|` | Of the expected matches, how many did the LLM find? |
| **MRR** (Mean Reciprocal Rank) | `mean(1 / rank_of_first_hit)` | How high up the list did the first correct match appear? Rank 1 → 1.0, rank 2 → 0.5, rank 3 → 0.33. |
| **Hit rate** | `cases with ≥1 hit / total cases` | Did the LLM find at least one expected match per query? |
| **Negative leak rate** | `cases that returned a must_not_match / total` | Did the LLM ever recommend someone it explicitly shouldn't? |
| **Accuracy** | `passing cases / total` (a case passes only if it has ≥1 hit AND no leaks) | Strict pass/fail per query — this is the headline number to compare against the 80% target. |

Run it from the UI ("▶️ Run Evaluation" in the Metrics tab) or from the CLI:

```powershell
cd backend
python -m evals.run_eval
# Optional: --k 5 for a wider window
```

Results are persisted to `backend/evals/last_run.json` and surfaced in the
dashboard with a per-case breakdown (PASS / MISS / LEAK).

The ground-truth file is intentionally hand-curated for the 31 candidates in
the current CSV. If you add or remove candidates, update `expected_candidates`
and `must_not_match` to keep the eval meaningful.

---

## Tests

```powershell
cd backend
pytest
```

52 tests covering: prompt-injection evasion (homoglyphs, whitespace,
zero-width chars), PII masking, evaluator math (precision/recall/MRR), audit
logging (append, redaction, truncation, filtering), CSV dedup &
add/update roundtrip.

---

## Architecture notes

- **Chroma is persistent**: on boot we open the existing index and only add
  documents that aren't already there. Ingest / refresh do an incremental
  upsert instead of rebuilding from scratch.
- **LLM is abstracted**: `ai/llm_provider.py` picks the chat model based on
  `LLM_PROVIDER`. Switching to an EEA provider is a one-line config change.
- **Output validation**: the RAG chain ends with a validator that strips
  sensitive keys and enforces the JSON schema before returning to the API.
- **PII by default**: `GET /api/candidates` masks emails (`a***@example.com`).
  Full contact info is only served by `/api/candidates/{name}/contact`, which
  writes an audit entry.
- **Audit log**: every state change appends to `data/audit.jsonl`. Read it via
  `GET /api/audit?limit=100&action=match`.
