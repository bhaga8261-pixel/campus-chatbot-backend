from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "campus_query_db"
    OPENAI_API_KEY: Optional[str] = None
    JWT_SECRET: str = "f78a7fbc22d4fca908271034f40f0c057635c02b28c89c8a99bb8e2efcfd6e7a"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_COLLECTION: str = "document_chunks"

    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
 
