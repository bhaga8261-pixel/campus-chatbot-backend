import logging
from typing import List
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Lazy load SentenceTransformer to avoid slow startup for simple commands
class EmbeddingService:
    def __init__(self):
        self.model = None

    def _load_model(self):
        if self.model is None:
            logger.info(f"Initializing embedding model '{settings.EMBEDDING_MODEL}'...")
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
                logger.info("SentenceTransformer model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load sentence-transformers: {e}. Falling back to mock embeddings.")
                self.model = "mock"

    def get_embedding(self, text: str) -> List[float]:
        """Generate a 384-dimensional vector embedding for a single text string."""
        self._load_model()
        if self.model == "mock":
            # Return a simple deterministic 384-dim dummy vector for fallback
            import math
            dummy = []
            for i in range(384):
                val = math.sin(hash(text) + i) * 0.1
                dummy.append(val)
            return dummy
        
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise e

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of text strings."""
        self._load_model()
        if self.model == "mock":
            return [self.get_embedding(t) for t in texts]
        
        try:
            embeddings = self.model.encode(texts)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating list of embeddings: {e}")
            raise e

embedding_service = EmbeddingService()
