"""PDF text extraction helper for CV uploads."""
import logging
import warnings

from langchain_community.document_loaders import PyPDFLoader

warnings.filterwarnings("ignore", category=UserWarning, module="PyPDFLoader")
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract the full text content from a PDF using PyPDFLoader."""
    try:
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        return "\n".join(page.page_content for page in pages)
    except Exception as e:
        logger.warning("Failed to read PDF %s: %s", file_path, e)
        return ""
