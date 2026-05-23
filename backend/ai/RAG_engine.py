import os
import warnings
from pathlib import Path
from dotenv import load_dotenv
from operator import itemgetter

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint, ChatHuggingFace
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

def normalize_path(value: str) -> str:
    value = value.strip().strip('"')
    value = value.replace('\\', '/')
    return str(Path(value).expanduser())

OBSIDIAN_VAULT_PATH = normalize_path(
    os.getenv("OBSIDIAN_VAULT_PATH", str(BASE_DIR / "obsidian_db" / "OBSIDIAN-DATA-POOL"))
)
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

    # CHUNKING STRATEGY: Păstrăm contextul întreg (5000), dar adăugăm overlap (200) pentru a nu rupe sensul
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=200)
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
    # LLM SETUP & LOWER TEMPERATURE: 0.01 elimină creativitatea (0 fix nu e permis de API)
    base_llm = HuggingFaceEndpoint(
        repo_id=os.getenv("HF_LLM_REPO_ID", "meta-llama/Meta-Llama-3-8B-Instruct"),
        temperature=0.01,
        max_new_tokens=1024,
        huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
    )
    
    llm = ChatHuggingFace(llm=base_llm)

    # SCHEMA VALIDATION: Forțează modelul să returneze doar JSON sau va pica.
    parser = JsonOutputParser()

    # STRICT PROMPT ENGINEERING: Reguli de fier împotriva halucinațiilor
    template = """
    You are a strict, objective "finder of facts" HR Talent Matcher. You are NOT a creative writer.
    
    HR Query: {input}
    
    Context from Obsidian Database:
    {context}
    
    CRITICAL RULES - ENFORCING STRICT GROUNDING:
    1. Base your answer STRICTLY on the provided context. 
    2. If the information is not in the context, do not invent information. Respond with an empty array: []
    3. Do not trust your internal knowledge. Use ONLY the role, title, skills, and languages as they appear in the candidate's profile context.
    4. REQUIRE CITATIONS: For the "citation" field, you must extract a short, exact snippet from the document that proves why this candidate matches.

    INSTRUCTIONS:
    Identify up to 3 best matching candidates from the context.
    You MUST respond with a valid JSON array of objects. Do not write anything else outside the JSON.
    Each object must exactly match these keys:
    - "initials": string
    - "name": string
    - "role": string (Strictly use the REAL current_role_title from the document)
    - "matchScore": integer (0-100)
    - "matchRank": string
    - "skillsScore": integer (0-100)
    - "expScore": integer (0-100)
    - "locationScore": integer (0-100)
    - "tags": array of 3 string skills (ONLY use real skills found)
    - "langs": string
    - "colorTheme": string (choose strictly from "purple", "green", "blue")
    - "citation": string (Short exact snippet from context proving the match)
    
    {format_instructions}
    """
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["input", "context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # CONFIDENCE THRESHOLDS: Dacă documentul găsit are scor sub 0.3 similaritate, e aruncat automat la gunoi.
    retriever = vector_db.as_retriever(
        search_type="similarity_score_threshold", 
        search_kwargs={"score_threshold": 0.3, "k": 3}
    )

    # METADATA FILTERING: Adăugăm numele fișierului sursă direct în text ca LLM-ul să știe pe cine citește.
    def format_docs(docs):
        return "\n\n".join(f"--- CANDIDATE FILE: {doc.metadata.get('source', 'Unknown')} ---\n{doc.page_content}" for doc in docs)

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