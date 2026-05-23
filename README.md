# CVision
AI Recruitment Assistant that helps companies identify the best-fit candidates faster, smarter, and more accurately than ATS

## Current project structure

CVision/
├── backend/                   # Python API + AI/RAG engine
│   ├── ai/                    # AI logic and vector retrieval
│   │   ├── __init__.py
│   │   └── RAG_engine.py      # Builds embeddings, vector DB, retriever chain
│   ├── obsidian_db/           # Local Obsidian vault copy for candidate markdown data
│   ├── scraper/               # Data ingestion helpers
│   │   └── parser.py          # Text extraction / parsing logic
│   ├── main.py                # FastAPI app and /api/match endpoint
│
├── frontend/                  # React + TypeScript UI
│   ├── dist/                  # Built production output
│   ├── node_modules/
│   ├── public/ (not present)
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── main.tsx
│   │   ├── vite-env.d.ts
│   │   └── components/
│   │       ├── CandidateCard.tsx
│   │       ├── CandidateCard.css
│   │       ├── ChatArea.tsx
│   │       ├── ChatArea.css
│   │       ├── Sidebar.tsx
│   │       └── Sidebar.css
│
├── obsidian_db/               # Root Obsidian data source for candidate notes
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables for backend config
├── .gitignore
└── README.md                  # Project documentation

## What the project does now

- `backend/main.py` launches a FastAPI server with a `/api/match` endpoint.
- `backend/ai/RAG_engine.py` loads Obsidian Markdown documents, builds embeddings with `HuggingFaceEmbeddings`, stores them in `ChromaDB`, and creates a retriever powered by LangChain.
- `frontend/src/App.tsx` renders the UI, sends HR queries to the backend, and displays matching candidates.
- Local Obsidian notes under `obsidian_db/` serve as the candidate knowledge base.

## Architecture overview

1. **Obsidian data layer**
   - Candidate profiles are stored as Markdown files.
   - Backend loads `.md` files from `backend/obsidian_db/` by default.

2. **Vectorization & retrieval**
   - `RAG_engine.py` uses a text splitter and `HuggingFaceEmbeddings` to create semantic vectors.
   - The vectors are persisted in a local ChromaDB directory.
   - A retrieval chain answers HR queries by combining retrieved context with an LLM prompt.

3. **API layer**
   - FastAPI exposes the matching endpoint.
   - The frontend posts queries to `http://127.0.0.1:8000/api/match` and receives candidate arrays.

4. **UI layer**
   - React app contains reusable components for the sidebar, chat input, and candidate cards.
   - Candidate data is displayed dynamically after backend matching.

## Current tech stack

- Backend: `Python 3.12`, `FastAPI`, `python-dotenv`
- AI / RAG: `langchain`, `langchain-community`, `langchain-huggingface`, `chromadb`, `sentence-transformers`
- Frontend: `React`, `TypeScript`, `Vite`, `lucide-react`

## Run locally

### Backend
```powershell
cd d:\buildathon\CVision
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend/main.py
```

### Frontend
```powershell
cd d:\buildathon\CVision\frontend
npm install
npm run dev
```

### Notes
- The backend uses `.env` values if present. By default it reads Obsidian files from `./obsidian_db` and stores Chroma data in `./chroma_storage`.
- The frontend imports components using `src/components/*` and requires `vite-env.d.ts` for CSS module resolution.

## Current project state

- The backend is implemented and can run as a FastAPI service.
- The frontend is implemented with a React + TypeScript dashboard.
- The current structure no longer includes the older `backend/api/`, `backend/database/`, or `backend/ai_core/` folders from the outdated design.
- The live candidate source is currently the Obsidian markdown dataset under `obsidian_db/`.
