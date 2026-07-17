import logging
from typing import List, Dict, Any
import numpy as np
from app.database.connection import get_collection
from app.services.embedding import embedding_service

logger = logging.getLogger(__name__)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate the cosine similarity between two vector lists."""
    arr1 = np.array(v1)
    arr2 = np.array(v2)
    dot = np.dot(arr1, arr2)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return float(dot / (norm1 * norm2))

async def perform_vector_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search document chunks for matches to a query string.
    First tries MongoDB Atlas Vector Search.
    Falls back to local Python cosine similarity search if Atlas search is not configured.
    """
    # 1. Generate query embedding
    try:
        query_vector = embedding_service.get_embedding(query)
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return []

    chunks_collection = get_collection("document_chunks")
    
    # 2. Try Atlas Vector Search
    try:
        # Atlas Vector Search uses aggregation pipeline with $vectorSearch stage
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Must match the Search Index name on Atlas
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 100,
                    "limit": limit
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "documentId": 1,
                    "chunk": 1,
                    "page": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        results = []
        async for doc in chunks_collection.aggregate(pipeline):
            results.append({
                "id": str(doc["_id"]),
                "documentId": str(doc.get("documentId")),
                "chunk": doc.get("chunk"),
                "page": doc.get("page"),
                "metadata": doc.get("metadata", {}),
                "score": doc.get("score", 0.0),
                "document_name": doc.get("metadata", {}).get("document_name", "Document")
            })
            
        if results:
            logger.info(f"Atlas Vector Search returned {len(results)} matches.")
            return results
            
    except Exception as ex:
        # Expected to fail if run on local MongoDB, or index is not set up on Atlas
        logger.warning(
            f"Atlas Vector Search failed/not configured: {ex}. "
            "Falling back to local cosine similarity search."
        )

    # 3. Local Cosine Similarity Fallback
    try:
        # Fetch all chunks (limit to 1000 to keep it performant for local dev)
        cursor = chunks_collection.find({}, {
            "_id": 1,
            "documentId": 1,
            "chunk": 1,
            "embedding": 1,
            "page": 1,
            "metadata": 1
        }).limit(1000)
        
        all_chunks = []
        async for doc in cursor:
            all_chunks.append(doc)
            
        if not all_chunks:
            logger.info("No documents found in database for search.")
            return []

        logger.info(f"Computing local cosine similarity across {len(all_chunks)} chunks...")
        scored_results = []
        for doc in all_chunks:
            chunk_embedding = doc.get("embedding")
            if not chunk_embedding or len(chunk_embedding) != len(query_vector):
                continue
            
            sim = cosine_similarity(query_vector, chunk_embedding)
            
            scored_results.append({
                "id": str(doc["_id"]),
                "documentId": str(doc.get("documentId")),
                "chunk": doc.get("chunk"),
                "page": doc.get("page"),
                "metadata": doc.get("metadata", {}),
                "score": sim,
                "document_name": doc.get("metadata", {}).get("document_name", "Document")
            })
            
        # Sort by similarity score descending
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = scored_results[:limit]
        
        logger.info(f"Local similarity search returned {len(top_results)} matches.")
        return top_results
        
    except Exception as e:
        logger.error(f"Local similarity fallback failed: {e}")
        return []
