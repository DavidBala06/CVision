import os
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_community.document_loaders import ObsidianLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

OBSIDIAN_VAULT_PATH = "./obsidian_db" 
CHROMA_DB_PATH = "./chroma_storage"
load_dotenv()

def build_vector_database():
    # Load documents from Obsidian vault
    loader = ObsidianLoader(OBSIDIAN_VAULT_PATH)
    documents = loader.load()
    
    if not documents:
        print("No documents found in the Obsidian vault")
        return None
    
    #Splits the documents into smaller chunks 
    text_splitter = RecursiveCharacterTextSplitter(chunk_size = 1000, chunk_overlap = 200)
    splits = text_splitter.split_documents(documents)
    
    # We use local embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name = "all-MiniLM-L6-v2",
        model_kwargs = {"device": "cpu"}) # cpu instead of cuda to avoid errors if no gpu
    
    #Create or update the Chroma vector database
    vector_db = Chroma.from_documents(
        documents = splits,
        embeddings = embeddings,
        persist_directory = CHROMA_DB_PATH
    )
    return vector_db

def create_retriever_chain(vector_db):
    # Set up the llm 
    llm = HuggingFaceEndpoint(
        repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
        temperature=0.1, 
        max_new_tokens=1024
    )
    
    # Create the prompt template for the retrieval chain
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
    
    # Configure the retrieval search for most 3 relevant documents
    retriver = vector_db.as_retriever(search_kwargs={"k": 3})
    
    #Answer question using the retrieved documents as context
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriver, question_answer_chain)
    
    return rag_chain

# if __name__ == "__main__":
#     # 0. Asigură-te că există folderul ca să nu dea eroare scriptul
#     os.makedirs(OBSIDIAN_VAULT_PATH, exist_ok=True)
    
#     # Creează un fișier de test dacă folderul e gol
#     test_file = os.path.join(OBSIDIAN_VAULT_PATH, "candidat_test.md")
#     if not os.path.exists(test_file):
#         with open(test_file, "w", encoding="utf-8") as f:
#             f.write("# David B.\nSenioritate: Mid-Level\nTehnologii: Python, LangChain, RAG, React\nLocație: Cluj-Napoca\nSumar: Pasionat de AI Automation Agencies și dezvoltare de sisteme LLM inteligente.")

#     # 1. Construim vectorii
#     db = build_vector_database()
    
#     if db:
#         # 2. Inițializăm motorul
#         matcher = create_retriever_chain(db)
        
#         # 3. Facem o căutare (Asta va veni din interfața utilizatorului / HR)
#         hr_query = "Caut pe cineva în Cluj care știe Python și are experiență cu LangChain pentru un proiect de AI."
#         print(f"\nHR a întrebat: {hr_query}\n")
#         print("AI-ul caută și analizează...\n")
        
#         response = matcher.invoke({"input": hr_query})
        
#         print("--- RĂSPUNS AI (SHORTLIST) ---")
#         print(response["answer"])