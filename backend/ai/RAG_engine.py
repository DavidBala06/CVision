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

# Rămânem pe Groq pentru că e super stabil și rapid
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
# Folderul chroma va fi salvat corect mereu în rădăcina proiectului
CHROMA_DB_PATH = normalize_path(os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_storage")))

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

    # Mărim chunk-ul ca profilurile să nu fie tăiate, prevenind halucinațiile
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=15000, chunk_overlap=0)
    splits = text_splitter.split_documents(documents)
    
    print(f"Loaded {len(documents)} documents, split into {len(splits)} chunks.")

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
    # Folosim versiunea 8B de la Llama 3.1
    # Are o limită gratuită de 30.000 TPM, deci nu vei mai primi "Request too large"
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.0
    )

    parser = JsonOutputParser()

    template = """
    You are a strict and objective HR Talent Matcher.
    
    HR Query: {input}
    
    Context from Obsidian Database:
    {context}
    
    CRITICAL RULES - DO NOT VIOLATE:
    1. DO NOT HALLUCINATE OR INVENT DATA. 
    2. You MUST use EXACTLY the role, title, skills, and languages as they appear in the candidate's profile context.
    3. If the candidate is a "Business Analyst", DO NOT label them a "Data Scientist" or anything else. Use their REAL current role.
    4. If the candidates in the context DO NOT fit the HR Query well enough, return an empty array: []
    5. Extract the REAL name and REAL initials. Do not guess.

    INSTRUCTIONS:
    Identify up to 3 best matching candidates from the context.
    You MUST respond with a valid JSON array of objects.
    Each object must exactly match these keys:
    - "initials": string
    - "name": string
    - "role": string (Strictly use the REAL current_role_title from the document)
    - "matchScore": integer (0-100)
    - "matchRank": string (e.g., "#1 match")
    - "skillsScore": integer (0-100)
    - "expScore": integer (0-100)
    - "locationScore": integer (0-100)
    - "tags": array of 3 string skills (ONLY use real skills found in their profile)
    - "langs": string (ONLY use real languages found, e.g., "EN · RO · IT")
    - "colorTheme": string (choose strictly from "purple", "green", "blue")
    
    {format_instructions}
    """
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["input", "context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Reducem k=3 pentru a extrage doar cei mai buni 3 candidați, înjumătățind dimensiunea promptului
    retriever = vector_db.as_retriever(search_kwargs={"k": 3})

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

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