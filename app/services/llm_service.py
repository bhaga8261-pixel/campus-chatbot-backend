import logging
from typing import List, Dict, Any, Tuple
from openai import AsyncOpenAI
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Initialize AsyncOpenAI client only if API key is provided
openai_client = None
if settings.OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
else:
    logger.warning("OPENAI_API_KEY is not set. The chatbot will operate in mock RAG mode.")

def format_context(chunks: List[Dict[str, Any]]) -> str:
    """Format matching chunks into a cohesive context string for the LLM prompt."""
    context_parts = []
    for idx, chunk in enumerate(chunks):
        doc_name = chunk.get("document_name", "Unknown Document")
        page = chunk.get("page", "?")
        text = chunk.get("chunk", "").strip()
        context_parts.append(f"--- Context Block {idx + 1} (Source: {doc_name}, Page {page}) ---\n{text}\n")
    return "\n".join(context_parts)

async def generate_rag_answer(query: str, chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Generate an answer using the retrieved context blocks and the OpenAI model.
    Falls back to a local heuristic summarizer if no OpenAI API Key is found.
    Returns (answer_string, list_of_sources).
    """
    sources = []
    seen = set()
    for chunk in chunks:
        doc_id = chunk.get("documentId")
        doc_name = chunk.get("document_name", "Document")
        page = chunk.get("page")
        # Deduplicate sources
        source_key = (doc_name, page)
        if source_key not in seen:
            seen.add(source_key)
            sources.append({
                "document_name": doc_name,
                "page": page,
                "documentId": doc_id
            })

    if not chunks:
        return "I could not find this information in the college documents.", []

    context_str = format_context(chunks)
    
    system_prompt = (
        "You are a helpful AI assistant for our college.\n"
        "Answer the user's question only using the provided document context below. "
        "Do not use external knowledge or make up facts. "
        "If the answer is unavailable in the context, clearly state that: "
        "'I could not find this information in the college documents.' and nothing else.\n"
        "Always mention the document name if available when explaining the answer.\n\n"
        f"College Context:\n{context_str}"
    )

    user_prompt = f"User Question: {query}"

    # Try calling OpenAI if client is available
    if openai_client is not None:
        try:
            logger.info("Sending prompt to OpenAI LLM...")
            # We use gpt-4o-mini as a cost-effective, fast model, or fallback to settings/defaults
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=500
            )
            answer = response.choices[0].message.content.strip()
            logger.info("Successfully received answer from OpenAI.")
            return answer, sources
        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}. Falling back to mock RAG mode.")

    # FALLBACK: Local Heuristic Mock RAG
    # We construct a response directly from the top matching context blocks
    logger.info("Executing Local Heuristic Mock RAG...")
    
    # Check if similarity score is too low (e.g., < 0.15) to prevent trash answers
    # But since we want to be responsive, let's look at the top chunk
    top_chunk = chunks[0]
    score = top_chunk.get("score", 0.0)
    
    if score < 0.15:
        return "I could not find this information in the college documents.", []

    doc_name = top_chunk.get("document_name", "Document")
    page = top_chunk.get("page", 1)
    chunk_text = top_chunk.get("chunk", "")
    
    # Try to make a clean extract
    # We can present the direct context snippet in a nice structured layout
    fallback_response = (
        f"**[Local RAG Mode - No OpenAI Key Configured]**\n\n"
        f"I found some relevant information in **{doc_name}** (Page {page}):\n\n"
        f"> {chunk_text}\n\n"
        f"*(Note: To get natural language synthesis, please configure a valid `OPENAI_API_KEY` in the `.env` file.)*"
    )
    return fallback_response, sources
