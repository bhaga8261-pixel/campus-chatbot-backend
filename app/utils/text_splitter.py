import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def split_document_pages(pages: List[Dict[str, Any]], chunk_size: int = 800, chunk_overlap: int = 150) -> List[Dict[str, Any]]:
    """
    Split extracted pages into smaller overlapping chunks.
    Returns a list of dictionaries with chunk text, page, and character index metadata.
    """
    chunks = []
    for page_obj in pages:
        text = page_obj["text"]
        page_num = page_obj["page"]
        
        # If page is empty or too short, keep it as is
        if len(text) <= chunk_size:
            chunks.append({
                "chunk": text,
                "page": page_num,
                "start_idx": 0,
                "end_idx": len(text)
            })
            continue
            
        # Sliding window chunking
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # If this is not the first chunk and it's very short, don't write a separate chunk
            if start > 0 and len(chunk_text) < 100:
                break
                
            chunks.append({
                "chunk": chunk_text,
                "page": page_num,
                "start_idx": start,
                "end_idx": min(end, len(text))
            })
            start += (chunk_size - chunk_overlap)
            
    logger.info(f"Split {len(pages)} pages into {len(chunks)} chunks using size={chunk_size}, overlap={chunk_overlap}.")
    return chunks
