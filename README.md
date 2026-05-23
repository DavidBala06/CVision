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

# 👁️ CVision: AI-Powered Talent Pool Manager

> **Linnify Hackathon Challenge** | *Simplifying life through innovation.*

CVision este un agent AI hibrid conceput pentru a automatiza și eficientiza procesele departamentelor de HR. Combinând puterea de vizualizare a unui **Knowledge Graph (via Obsidian)** cu capabilitățile analitice ale **Vector RAG (ChromaDB)**, sistemul nostru transformă datele brute în decizii de recrutare inteligente, sigure și conforme cu standardele GDPR.

---

## 🚀 Problema vs. Soluția CVision

Gestionarea unei baze de date cu candidați este un proces consumator de timp, predispus la date învechite (outdated) și la oportunități ratate. 

**Abordarea noastră:** În loc să construim un simplu tabel, am creat o arhitectură **"Graph-RAG ready"**. 
* **Vizual & Conectat:** Folosim Obsidian ca interfață de Knowledge Graph pentru ca echipa de HR să vadă instantaneu rețeaua de candidați și tehnologii.
* **Inteligent & Semantic:** Folosim un motor RAG vectorial (ChromaDB + LangChain) care "înțelege" experiența candidaților și face un shortlisting bazat pe context, nu doar pe cuvinte cheie.

---

## 🛡️ Cum am respectat Constrângerile Critice (Compliance & Security)

Am construit CVision având securitatea ca prioritate zero:

1. **🔒 Human-in-the-Loop (Strict):** Agentul AI funcționează exclusiv ca un asistent de recomandare. El **nu** modifică datele singur și **nu** trimite email-uri automat. El propune *drafturi* și *shortlist-uri* care necesită mereu aprobarea finală a unui operator uman (HR).
2. **🇪🇺 GDPR & Data Privacy:** Ingestia datelor (parsarea CV-urilor/PDF-urilor) și procesarea lor se face anonimizat sau prin modele sigure. Stocarea vectorilor (ChromaDB) și a bazei de date (Obsidian `.md` files) este **100% locală**, asigurând reținerea datelor în spațiul EEA (European Economic Area). Nu există scurgeri de date către terți.
3. **📊 Success Metrics (LangChain):** Arhitectura RAG este construită pe framework-ul LangChain, permițând implementarea de evaluatori automați (precum Ragas) pentru a asigura o acuratețe țintă de peste 80% în maparea candidaților pe roluri.

---

## ⚙️ Module și Funcționalități

### 1. Ingestia și Extragerea Datelor (Adapter Pattern)
* Sistemul citește fișiere locale (CV-uri în format PDF sau profiluri HTML).
* Utilizează LLM-uri (via Hugging Face API / LLM Local) pentru extragerea structurată (NER - Named Entity Recognition) a datelor: *Nume, Senioritate, Tehnologii, Sumar Experiență*.
* Exportă datele direct ca fișiere Markdown legate (Graful Obsidian) și ca embeddings în baza vectorială.

### 2. Mentenanța Bazei de Date
* Actualizare ușoară prin rescrierea proprietăților nodurilor în graf. 
* Informațiile sunt versionate temporal (ex: `last_updated`), permițând HR-ului să identifice rapid profilele care necesită un "Bulk Refresh".

### 3. Shortlisting Inteligent (RAG Matcher)
* HR-ul introduce o descriere a jobului (JD).
* ChromaDB scanează talent pool-ul, făcând o căutare semantică pe istoricul proiectelor candidaților și returnează "Top Matches" alături de un raționament generat de AI (*"De ce se potrivește acest candidat?"*).

### 4. Generarea de Drafturi pentru Outreach
* Pe baza potrivirii dintre candidat și job, agentul redactează automat un draft de email personalizat, gata să fie revizuit și expediat de echipa operațională.

---

## 💻 Tech Stack

* **Backend / AI Logic:** `Python 3.10+`, `FastAPI`
* **AI & RAG Framework:** `LangChain`, `HuggingFace API` (Mixtral/Llama3)
* **Bază de Date Vectorială:** `ChromaDB` (Local spatial index)
* **Knowledge Graph & HR UI:** `Obsidian` (pentru vizualizarea nodurilor și Human-in-the-Loop)
* **Procesare Date:** `PyPDFLoader`, `Pydantic` (pentru JSON enforcement)

---

## 🛠️ Cum se rulează proiectul (Local Setup)
Urmați acești pași pentru a porni sistemul pe mașina locală:

**1. Clonarea proiectului și setup-ul mediului virtual:**
```bash
git clone [https://github.com/your-username/cvision-talent-manager.git](https://github.com/your-username/cvision-talent-manager.git)
cd cvision-talent-manager
python -m venv venv
# Pe Windows:
venv\Scripts\activate
# Pe Linux/Mac:
source venv/bin/activate