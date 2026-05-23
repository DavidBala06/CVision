import os
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint, ChatHuggingFace
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

load_dotenv()

OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "./obsidian_db")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_storage")


def _make_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )


def build_vector_database(force_rebuild: bool = False):
    os.makedirs(OBSIDIAN_VAULT_PATH, exist_ok=True)

    embeddings = _make_embeddings()

    if os.path.isdir(CHROMA_DB_PATH) and os.listdir(CHROMA_DB_PATH) and not force_rebuild:
        print(f"Loading existing Chroma DB from '{CHROMA_DB_PATH}'")
        return Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=embeddings)

    loader = DirectoryLoader(
        OBSIDIAN_VAULT_PATH,
        glob="candidates/**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
        silent_errors=True,
        show_progress=False,
    )
    documents = loader.load()

    # Within each candidate folder, exclude the linkedin/cv export under
    # attachments/ — they share generic structure and dilute retrieval.
    documents = [
        d for d in documents
        if "attachments" not in d.metadata.get("source", "").replace("\\", "/").split("/")
    ]

    if not documents:
        print(f"No documents found in the Obsidian vault at '{OBSIDIAN_VAULT_PATH}'")
        return None

    print(f"Indexing {len(documents)} candidate cards from '{OBSIDIAN_VAULT_PATH}'")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)

    vector_db = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )
    return vector_db


def _build_llm():
    """Pick the best available LLM. Anthropic Claude is preferred."""
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        print(f"LLM provider: Anthropic Claude ({model})")
        return ChatAnthropic(
            model=model,
            temperature=0.1,
            max_tokens=1024,
        )

    llm_repo_id = os.getenv("HF_LLM_REPO_ID", "mistralai/Mistral-7B-Instruct-v0.3")
    print(f"LLM provider: HuggingFace Inference ({llm_repo_id})")
    endpoint = HuggingFaceEndpoint(
        repo_id=llm_repo_id,
        task="conversational",
        temperature=0.1,
        max_new_tokens=1024,
    )
    return ChatHuggingFace(llm=endpoint)


def create_retriever_chain(vector_db):
    llm = _build_llm()

    template = """
    You are an expert HR Talent Matcher. Using the provided context (which contains candidate profiles from our database),
    answer the HR manager's query. Identify the best candidates and explain why they match.

    IMPORTANT: You MUST return exactly a JSON array of up to 3 candidate objects. Do not add any markdown formatting like ```json. Just output the raw JSON array.
    Each object MUST have the following keys:
    - "initials": string (e.g. "AM")
    - "name": string
    - "role": string (e.g. "Senior PM · Bucharest")
    - "matchScore": number (overall match percentage 0-100)
    - "matchRank": string (e.g. "#1 match")
    - "skillsScore": number (0-100)
    - "expScore": number (0-100)
    - "locationScore": number (0-100)
    - "tags": array of 3 string skills
    - "langs": string (e.g. "EN · RO")
    - "colorTheme": string (choose from "purple", "green", "blue")

    If you don't find any good match, return an empty array [].

    Context from Obsidian Database:
    {context}

    HR Query: {input}

    Response (RAW JSON ARRAY ONLY):
    """
    prompt = PromptTemplate.from_template(template)

    retriever = vector_db.as_retriever(search_kwargs={"k": 3})

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain


if __name__ == "__main__":
    os.makedirs(OBSIDIAN_VAULT_PATH, exist_ok=True)

    db = build_vector_database()
    if db:
        matcher = create_retriever_chain(db)

        hr_query = "Caut pe cineva in Cluj care stie Python si are experienta cu LangChain pentru un proiect de AI."
        print(f"\nHR a intrebat: {hr_query}\n")
        response = matcher.invoke({"input": hr_query})

        print("--- RASPUNS AI (SHORTLIST) ---")
        print(response["answer"])
