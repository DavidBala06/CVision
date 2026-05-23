# CVision
AI Recruitment Assistant that helps comanies identify the best-fit candidates faster, smarter, and more accurately than ATS

cvision-talent-manager/
├── backend/                # Python 3.10+ (FastAPI)
│   ├── api/                # Rutele de comunicare (ex: /upload-cv, /match-job)
│   ├── ai_core/            # Creierul aplicației
│   │   ├── llm_client.py   # Conexiunea cu Hugging Face API via LangChain
│   │   ├── rag_engine.py   # Logica de vectorizare și Graph/RAG
│   │   └── prompts.py      # Template-urile de instrucțiuni
│   ├── scraper/            # Modulul de Ingestion
│   │   ├── parser.py       # Extragerea textului din PDF-uri locale
│   │   └── linkedin.py     # Logica de scraping / curățare HTML
│   ├── database/           # Conexiunile la baze de date
│   │   ├── vector_db.py    # Setup-ul pentru ChromaDB / Qdrant
│   │   └── relational.py   # Setup-ul pentru SQLite/Postgres (pentru HR)
│   ├── requirements.txt
│   └── main.py             # Entry-point-ul serverului FastAPI
│
├── frontend/               # TypeScript (React / Next.js)
│   ├── src/
│   │   ├── components/     # UI: HR Dashboard, Candidate Table, Email Modal
│   │   ├── services/       # Apelurile API către backend-ul de Python
│   │   ├── types/          # Interfețele TS (ex: type Candidate = { name: string... })
│   │   └── App.tsx         # Punctul de start al UI-ului
│   ├── package.json
│   └── tsconfig.json
│
└── README.md               # Documentația pentru hackathon (CRITIC pentru juriu)