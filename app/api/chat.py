import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.jwt_handler import get_current_user
from app.database.connection import get_collection
from app.models.models import ChatQuestion, ChatResponse
from app.services.vector_search import perform_vector_search
from app.services.llm_service import generate_rag_answer
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chatbot"])

@router.post("", response_model=ChatResponse)
async def ask_chatbot(
    payload: ChatQuestion,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit a student query to the RAG pipeline.
    Performs vector search across documents, builds prompt, calls LLM, and logs the conversation.
    """
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
        
    start_time = datetime.utcnow()
    logger.info(f"Chat request by {current_user.get('email')}: '{question}'")

    try:
        # Step 1: Retrieve top 5 matching chunks from Vector search
        chunks = await perform_vector_search(question, limit=5)
        
        # Step 2: Generate response using LLM (or fallback)
        answer, sources = await generate_rag_answer(question, chunks)
        
        latency = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Chat response generated in {latency:.2f} seconds. Sources found: {len(sources)}")
        
        # Step 3: Save chat interaction to DB
        chats_collection = get_collection("chats")
        chat_doc = {
            "userId": ObjectId(current_user["_id"]),
            "question": question,
            "answer": answer,
            "timestamp": datetime.utcnow(),
            "sources": sources
        }
        
        result = await chats_collection.insert_one(chat_doc)
        chat_doc["_id"] = result.inserted_id
        
        return chat_doc

    except Exception as e:
        logger.error(f"Chatbot RAG execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while answering your question: {str(e)}"
        )

@router.get("/history", response_model=List[ChatResponse])
async def get_chat_history(current_user: dict = Depends(get_current_user)):
    """Retrieve chat logs history for the current user, ordered by date."""
    chats_collection = get_collection("chats")
    cursor = chats_collection.find({"userId": ObjectId(current_user["_id"])}).sort("timestamp", 1)
    
    history = []
    async for chat in cursor:
        history.append(chat)
        
    return history

@router.delete("/history", status_code=status.HTTP_200_OK)
async def clear_chat_history(current_user: dict = Depends(get_current_user)):
    """Delete all logged chats for the current user."""
    chats_collection = get_collection("chats")
    result = await chats_collection.delete_many({"userId": ObjectId(current_user["_id"])})
    
    logger.info(f"User {current_user['email']} cleared their chat history. {result.deleted_count} messages deleted.")
    return {"message": "Chat history cleared successfully", "deleted_count": result.deleted_count}
