import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db_helper = MongoDB()

async def connect_to_mongo():
    logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
    try:
        db_helper.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db_helper.db = db_helper.client[settings.DATABASE_NAME]
        # Ping the database to verify connectivity
        await db_helper.client.admin.command('ping')
        logger.info("Connected to MongoDB successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_helper.client:
        db_helper.client.close()
        logger.info("MongoDB connection closed.")

def get_db():
    return db_helper.db

def get_collection(name: str):
    if db_helper.db is None:
        raise RuntimeError("Database connection not initialized. Call connect_to_mongo first.")
    return db_helper.db[name]
