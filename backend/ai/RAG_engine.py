import os
import warnings
from dotenv import load_dotenv
from lan

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from langchain_community.document_loaders import ObsidianLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

# OBSIDIAN_VAULT_PATH = "./obsidian_db" 
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
    text_splitter = RecursiveCharacterTextSplitter(chunck_size = 1000, chunk_overlap = 200)
    splits = text_splitter.split_documents(documents)
    
    # We use local embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name = "all-MiniLM-L6-v2",
        model_kwargs = {"device": "cuda"})
    
    #Create or update the Chroma vector database
    vector_db = Chroma.from_documents(
        docuemnts = splits,
        embeddings = embeddings,
        persist_directory = CHROMA_DB_PATH
    )
    return vector_db

def create_retriever_chain(vector_db):
    # Set up the llm 
    llm = HuggingFaceEndpoint(
        repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
        temperature=0.1, 
        max_new_tokens=512
    )
    
    # Create the prompt template for the retrieval chain
    template = """
    You are an expert HR Talent Matcher. Using the provided context (which contains candidate profiles from our database), 
    answer the HR manager's query. Identify the best candidates and briefly explain WHY they match.
    If you don't find a good match in the context, say "Nu am găsit un candidat potrivit în baza de date curentă."
    
    Context from Obsidian Database:
    {context}
    
    HR Query: {input}
    
    Response:
    """
    prompt = PromptTemplate.from_template(template)
    
    # Configure the retrieval search for most 3 relevant documents
    retriver = vector_db.as_retriever(search_kwargs={"k": 3})
    
    #Answer question using the retrieved documents as context
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriver, question_answer_chain)
    
    return rag_chain
