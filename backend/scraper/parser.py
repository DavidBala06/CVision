from langchain_community.document_loaders import PyPDFLoader
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="PyPDFLoader")

def extract_text_from_pdf(file_path: str) -> str:
    # Folosim PyPDFLoader pentru a extrage textul din PDF
    try:
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        
        # Combinăm textul de pe toate paginile
        full_text = "\n".join([page.page_content for page in pages])
        return full_text
    
    except Exception as e:
        print(f"Nu am putut citi PDF-ul {file_path}: {e}")
        return ""