"""
RAG Engine 

Shortlisting — scan talent pool CSV, rank candidates for a job.
Uses Chroma vector store + Groq LLM for semantic search and ranking, maybe we will switch to huggingface, i dont trust groq
"""
import os
import csv
import warnings
from pathlib import Path
from dotenv import load_dotenv
from operator import itemgetter

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.documents import Document

from ai.guardrails import sanitize_input, validate_json_output, get_system_guardrail_prompt

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = Path(os.getenv("CSV_PATH", str(BASE_DIR / "data" / "talent_pool.csv")))
CHROMA_DB_PATH = str(BASE_DIR / "chroma_csv_storage")


def load_csv_as_documents() -> list[Document]:
    # Load each CSV row as a LangChain Document for vector indexing.
    if not CSV_PATH.exists():
        print(f"CSV not found at {CSV_PATH}")
        return []

    documents = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Build rich text content from all fields
            content_parts = [
                f"Name: {row.get('name', '')}",
                f"Seniority: {row.get('seniority', '')}",
                f"Years of Experience: {row.get('years_of_experience', '')}",
                f"Current Role: {row.get('current_role', '')}",
                f"Previous Jobs: {row.get('previous_jobs', '')}",
                f"Degrees: {row.get('degrees', '')}",
                f"Location: {row.get('location', '')}",
                f"Languages: {row.get('languages', '')}",
                f"Technologies: {row.get('technologies', '')}",
                f"Project Summary: {row.get('project_summary', '')}",
            ]
            
            # Filter out empty fields
            content = "\n".join(p for p in content_parts if not p.endswith(": "))
            
            metadata = {
                "name": row.get("name", ""),
                "seniority": row.get("seniority", ""),
                "location": row.get("location", ""),
                "technologies": row.get("technologies", ""),
                "linkedin_url": row.get("linkedin_url", ""),
                "github_url": row.get("github_url", ""),
                "email": row.get("email", ""),
                "status": row.get("status", ""),
            }
            
            documents.append(Document(page_content=content, metadata=metadata))

    return documents


def build_vector_database():
    #Build Chroma vector database from CSV talent pool.
    print(f"Loading talent pool from: {CSV_PATH}")

    documents = load_csv_as_documents()

    if not documents:
        print(f"No candidates found in CSV at '{CSV_PATH}'")
        return None

    print(f"Loaded {len(documents)} candidate profiles from CSV.")

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    # Rebuild vector store each time (CSV is small, fast to index)
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )
    return vector_db


def create_retriever_chain(vector_db):
    #Create the RAG chain for candidate matching.
    if vector_db is None:
        return None

    # LLM: Groq with Llama 3.3 
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.01,
        max_tokens=2048,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )

    parser = JsonOutputParser()

    # Strict prompt with guardrails
    prompt = ChatPromptTemplate.from_messages([
        ("system", get_system_guardrail_prompt() + """
You are a strict, objective HR Talent Matcher. You find the best candidates from a talent pool CSV database.

CRITICAL RULES — STRICT GROUNDING:
1. Base your answer STRICTLY on the provided context from the talent pool.
2. If no candidates match, return an empty array: []
3. Do NOT invent or hallucinate candidate information.
4. REQUIRE CITATIONS: extract a short exact snippet proving the match.
5. The LinkedIn URL must come from the context data — do NOT fabricate URLs.

INSTRUCTIONS:
Identify up to 3 best matching candidates from the context.
Respond ONLY with a valid JSON array. No text outside the JSON.

Each object must have these exact keys:
- "initials": string (first letters of first and last name)
- "name": string
- "role": string (use the REAL current_role from the data)
- "matchScore": integer (0-100)
- "matchRank": string ("Excellent", "Good", or "Fair")
- "skillsScore": integer (0-100)
- "expScore": integer (0-100)
- "locationScore": integer (0-100)
- "tags": array of 3 string skills (ONLY real skills from data)
- "langs": string (languages spoken)
- "linkedin_url": string (from data, or "" if not available)
- "citation": string (exact snippet from context proving the match)
- "colorTheme": string ("purple", "green", or "blue")

{format_instructions}
"""),
        ("human", """HR Query: {input}

Candidate profiles from Talent Pool CSV:
{context}""")
    ])

    retriever = vector_db.as_retriever(search_kwargs={"k": 5})

    def format_docs(docs):
        return "\n\n".join(
            f"--- CANDIDATE #{i+1} ---\n{doc.page_content}\nLinkedIn: {doc.metadata.get('linkedin_url', 'N/A')}\nGitHub: {doc.metadata.get('github_url', 'N/A')}"
            for i, doc in enumerate(docs)
        )

    rag_chain = (
        {
            "context": itemgetter("input") | retriever | format_docs,
            "input": itemgetter("input"),
        }
        | prompt
        | llm
        | parser
    )

    return rag_chain