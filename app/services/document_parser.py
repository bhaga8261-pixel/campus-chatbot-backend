import io
import logging
from typing import List, Dict, Any
import PyPDF2
import docx

logger = logging.getLogger(__name__)

def parse_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extract text page-by-page from a PDF byte stream.
    Returns a list of dictionaries with text and page number (1-indexed).
    """
    pages = []
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        num_pages = len(pdf_reader.pages)
        logger.info(f"Parsing PDF with {num_pages} pages...")
        
        for page_idx in range(num_pages):
            page_text = pdf_reader.pages[page_idx].extract_text()
            if page_text and page_text.strip():
                pages.append({
                    "text": page_text.strip(),
                    "page": page_idx + 1
                })
        logger.info(f"Successfully parsed {len(pages)} readable pages from PDF.")
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        raise ValueError(f"Failed to parse PDF document: {str(e)}")
    
    return pages

def parse_docx(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extract text from a DOCX byte stream.
    Since DOCX is flowable, we create pseudo-pages by grouping paragraphs.
    Returns a list of dictionaries.
    """
    pages = []
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        logger.info(f"Parsing DOCX with {len(paragraphs)} non-empty paragraphs...")
        
        # Group paragraphs to create pseudo-pages (e.g., 5 paragraphs per page)
        paragraphs_per_page = 5
        current_page_text = []
        page_num = 1
        
        for idx, para in enumerate(paragraphs):
            current_page_text.append(para)
            if (idx + 1) % paragraphs_per_page == 0 or idx == len(paragraphs) - 1:
                text_block = "\n\n".join(current_page_text)
                pages.append({
                    "text": text_block,
                    "page": page_num
                })
                current_page_text = []
                page_num += 1
                
        logger.info(f"Successfully grouped DOCX into {len(pages)} pseudo-pages.")
    except Exception as e:
        logger.error(f"Error parsing DOCX: {e}")
        raise ValueError(f"Failed to parse DOCX document: {str(e)}")
        
    return pages

def parse_txt(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extract text from a plain text byte stream.
    Splits text into chunks of roughly 1500 characters as pseudo-pages.
    """
    pages = []
    try:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
        logger.info(f"Parsing TXT file with {len(text)} characters...")
        
        chunk_size = 1500
        page_num = 1
        
        # Split text by characters but try to split at double newline if possible, or just exact chunk size
        i = 0
        while i < len(text):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                pages.append({
                    "text": chunk.strip(),
                    "page": page_num
                })
                page_num += 1
            i += chunk_size
            
        logger.info(f"Successfully split TXT into {len(pages)} pseudo-pages.")
    except Exception as e:
        logger.error(f"Error parsing TXT: {e}")
        raise ValueError(f"Failed to parse TXT file: {str(e)}")
        
    return pages

def extract_text(filename: str, file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Dispatches file to the appropriate parser based on file extension.
    Returns a list of dicts: [{"text": str, "page": int}]
    """
    ext = filename.split(".")[-1].lower()
    if ext == "pdf":
        return parse_pdf(file_bytes)
    elif ext == "docx":
        return parse_docx(file_bytes)
    elif ext in ["txt", "md"]:
        return parse_txt(file_bytes)
    else:
        logger.error(f"Unsupported file format: {ext}")
        raise ValueError(f"Unsupported file format: .{ext}")
