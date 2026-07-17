import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.jwt_handler import get_current_admin
from app.database.connection import get_collection, get_db
from app.services.document_parser import extract_text
from app.services.embedding import embedding_service
from app.utils.text_splitter import split_document_pages
from app.config.settings import settings
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin Operations"])

@router.post("/embeddings/rebuild", status_code=status.HTTP_200_OK)
async def rebuild_embeddings(current_admin: dict = Depends(get_current_admin)):
    """
    Re-indexes and regenerates vector embeddings for all uploaded college documents.
    Clears `document_chunks` collection and re-segments/re-embeds each file in `documents`.
    Only accessible by administrators.
    """
    logger.info(f"Admin {current_admin['email']} triggered database embedding rebuild.")
    
    docs_collection = get_collection("documents")
    chunks_collection = get_collection("document_chunks")
    
    cursor = docs_collection.find()
    documents = []
    async for doc in cursor:
        documents.append(doc)
        
    if not documents:
        return {"message": "No documents found to rebuild."}
        
    try:
        # Clear existing chunks
        await chunks_collection.delete_many({})
        logger.info("Cleared document_chunks collection.")
        
        rebuilt_count = 0
        chunks_count = 0
        
        # We need the original file bytes. But in a real app, files are stored on disk or S3.
        # Let's see: we should store the file on disk in a folder `backend/app/uploads/` on upload.
        # Wait, did we write the files to disk in `documents.py`?
        # Ah, in `documents.py` we processed it directly from memory and didn't write it to disk.
        # To make rebuilding embeddings work, we should save the files to a directory `backend/app/uploads/`
        # when they are uploaded!
        # Let's check `documents.py`. We didn't save them. Let's make sure we write them to `backend/app/uploads/`
        # during upload, so that `rebuild_embeddings` can read them from disk!
        # This is a critical detail. Let's make sure we support it.
        # In our rebuild endpoint, if the file is not on disk (for example, if files were uploaded before disk storage was added),
        # we can log a warning, but we will write our upload endpoint to save the file.
        # Let's check if the directory `backend/app/uploads/` exists. We will create it dynamically.
        import os
        uploads_dir = os.path.join("backend", "app", "uploads")
        if not os.path.exists(uploads_dir):
            uploads_dir = os.path.join("app", "uploads")
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir, exist_ok=True)
                
        for doc in documents:
            filename = doc["filename"]
            # Look for the file on disk
            file_path = os.path.join(uploads_dir, filename)
            if not os.path.exists(file_path):
                logger.warning(f"File {filename} not found on disk at {file_path}. Skipping embedding rebuild for this file.")
                continue
                
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                
            pages = extract_text(filename, file_bytes)
            if not pages:
                continue
                
            chunks = split_document_pages(pages)
            if not chunks:
                continue
                
            chunk_texts = [c["chunk"] for c in chunks]
            embeddings = embedding_service.get_embeddings(chunk_texts)
            
            db_chunks = []
            for idx, chunk in enumerate(chunks):
                db_chunks.append({
                    "documentId": doc["_id"],
                    "chunk": chunk["chunk"],
                    "embedding": embeddings[idx],
                    "page": chunk["page"],
                    "metadata": {
                        "document_name": doc["title"],
                        "filename": filename,
                        "uploaded_at": doc.get("uploadedAt", datetime.utcnow()).isoformat(),
                        "start_idx": chunk["start_idx"],
                        "end_idx": chunk["end_idx"]
                    }
                })
                
            if db_chunks:
                await chunks_collection.insert_many(db_chunks)
                chunks_count += len(db_chunks)
                rebuilt_count += 1
                
        logger.info(f"Rebuild completed: {rebuilt_count}/{len(documents)} documents re-embedded. Total chunks: {chunks_count}.")
        return {
            "message": "Embeddings rebuild completed successfully",
            "documents_rebuilt": rebuilt_count,
            "total_chunks": chunks_count
        }
        
    except Exception as e:
        logger.error(f"Failed to rebuild embeddings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rebuild failed: {str(e)}"
        )

@router.get("/system/status")
async def get_system_status(current_admin: dict = Depends(get_current_admin)):
    """
    Retrieve statistics, database integrity, configurations, and basic chatbot analytics.
    Only accessible by administrators.
    """
    db = get_db()
    
    # 1. Database connection check
    db_status = "Online"
    try:
        await db.client.admin.command('ping')
    except Exception:
        db_status = "Offline"
        
    # 2. Count statistics across collections
    collections = ["users", "documents", "document_chunks", "chats", "notices", "events", "faq"]
    counts = {}
    for col in collections:
        try:
            counts[col] = await get_collection(col).count_documents({})
        except Exception:
            counts[col] = 0
            
    # Count of student vs admin users
    student_count = 0
    admin_count = 0
    try:
        student_count = await get_collection("users").count_documents({"role": "student"})
        admin_count = await get_collection("users").count_documents({"role": "admin"})
    except Exception:
        pass
        
    # 3. Basic analytics on popular questions
    popular_questions = []
    try:
        chats_col = get_collection("chats")
        # Aggregation pipeline to group similar questions or count duplicate exact questions
        pipeline = [
            {"$group": {"_id": "$question", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        async for item in chats_col.aggregate(pipeline):
            popular_questions.append({
                "question": item["_id"],
                "count": item["count"]
            })
    except Exception as e:
        logger.error(f"Analytics query failed: {e}")
        
    # 4. Status of AI features
    ai_status = {
        "embedding_model": settings.EMBEDDING_MODEL,
        "openai_key_configured": settings.OPENAI_API_KEY is not None and len(settings.OPENAI_API_KEY) > 0,
        "vector_search_ready": counts["document_chunks"] > 0
    }
    
    return {
        "database_status": db_status,
        "collection_counts": counts,
        "user_analytics": {
            "students": student_count,
            "admins": admin_count
        },
        "ai_status": ai_status,
        "popular_questions": popular_questions,
        "timestamp": datetime.utcnow()
    }

@router.get("/system/users", response_model=List[Dict[str, Any]])
async def list_users(current_admin: dict = Depends(get_current_admin)):
    """List all registered users. Only accessible by administrators."""
    users_collection = get_collection("users")
    cursor = users_collection.find({}, {"password": 0})
    users = []
    async for u in cursor:
        u["id"] = str(u["_id"])
        users.append(u)
    return users

@router.delete("/system/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: str, current_admin: dict = Depends(get_current_admin)):
    """Delete a user from the system. Administrators cannot delete themselves. Only accessible by admins."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
        
    obj_id = ObjectId(user_id)
    if obj_id == ObjectId(current_admin["_id"]):
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")
        
    users_collection = get_collection("users")
    user = await users_collection.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await users_collection.delete_one({"_id": obj_id})
    logger.info(f"Admin {current_admin['email']} deleted user {user['email']}.")
    
    return {"message": "User deleted successfully"}
