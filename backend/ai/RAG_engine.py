import os
import warnings
from pathlib import Path
from dotenv import load_dotenv
from operator import itemgetter

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Importul oficial pentru conectarea la Groq API
from langchain_groq import ChatGroq

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

def normalize_path(value: str) -> str:
    value = value.strip().strip('"')
    value = value.replace('\\', '/')
    return str(Path(value).expanduser())

OBSIDIAN_VAULT_PATH = normalize_path(
    os.getenv("OBSIDIAN_VAULT_PATH", str(BASE_DIR / "obsidian_db" / "OBSIDIAN-DATA-POOL"))
)
CHROMA_DB_PATH = normalize_path(os.getenv("CHROMA_DB_PATH", "./chroma_storage"))

def build_vector_database():
    print(f"Loading Obsidian vault from: {OBSIDIAN_VAULT_PATH}")
    os.makedirs(OBSIDIAN_VAULT_PATH, exist_ok=True)

    loader = DirectoryLoader(
        OBSIDIAN_VAULT_PATH,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
        silent_errors=True,
        show_progress=False,
    )
    documents = loader.load()

    if not documents:
        print(f"No documents found in the Obsidian vault at '{OBSIDIAN_VAULT_PATH}'")
        return None

    # Păstrăm profilul de candidat intact mărind dimensiunea fragmentului
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=0)
    splits = text_splitter.split_documents(documents)
    
    print(f"Loaded {len(documents)} documents, split into {len(splits)} chunks.")

    # Generarea locală a embeddings pe procesor (CPU)
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    vector_db = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )
    return vector_db

def create_retriever_chain(vector_db):
    # LLM-ul rulează prin Groq pentru performanță ultra-rapidă și stabilă
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1
    )

    parser = JsonOutputParser()

    template = """
    You are an expert HR Talent Matcher. Analyze the provided candidate profiles in the context and match them to the HR Query.
    
    HR Query: {input}
    
    Context from Obsidian Database:
    {context}
    
    INSTRUCTIONS:
    Identify up to 3 best matching candidates from the context.
    You MUST respond with a valid JSON array of objects. Do not write anything else outside the JSON.
    Each object must exactly match these keys:
    - "initials": string (e.g., "AB")
    - "name": string
    - "role": string (e.g., "Data Scientist")
    - "matchScore": integer (0-100)
    - "matchRank": string (e.g., "#1 match")
    - "skillsScore": integer (0-100)
    - "expScore": integer (0-100)
    - "locationScore": integer (0-100)
    - "tags": array of 3 string skills (e.g., ["Python", "Machine Learning", "SQL"])
    - "langs": string (e.g., "EN · RO")
    - "colorTheme": string (choose strictly from "purple", "green", "blue")
    
    If no candidates match, return: []
    
    {format_instructions}
    """
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["input", "context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    retriever = vector_db.as_retriever(search_kwargs={"k": 5})

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # FIX CRITIC: itemgetter("input") extrage textul brut, prevenind eroarea 'dict' has no attribute 'replace'
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

if __name__ == "__main__":
    db = build_vector_database()
    if db:
        matcher = create_retriever_chain(db)
        hr_query = "Caut un Python Developer."
        print(f"\nHR a intrebat: {hr_query}\n")
        response = matcher.invoke({"input": hr_query})
        print("--- RASPUNS AI (PARSED) ---")
        print(response)