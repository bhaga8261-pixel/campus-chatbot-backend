import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.api.router import api_router

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for FastAPI startup and shutdown."""
    logger.info("Initializing Campus Query Chatbot Backend...")
    # Initialize MongoDB connection
    await connect_to_mongo()
    yield
    # Close MongoDB connection
    await close_mongo_connection()
    logger.info("Campus Query Chatbot Backend shutdown complete.")

app = FastAPI(
    title="Campus Query Chatbot API",
    description="FastAPI Backend for AI-powered College Information Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware
# Allow Vite frontend local address and other potential client routes
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes
app.include_router(api_router)

@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint verifying backend health status."""
    return {
        "status": "healthy",
        "message": "Welcome to the Campus Query Chatbot API",
        "api_docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
