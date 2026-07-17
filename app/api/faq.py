import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.jwt_handler import get_current_admin, get_current_user
from app.database.connection import get_collection
from app.models.models import FAQCreate, FAQResponse
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/faq", tags=["FAQ"])

@router.post("", response_model=FAQResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(
    payload: FAQCreate,
    current_admin: dict = Depends(get_current_admin)
):
    """Create a new FAQ entry. Only accessible by administrators."""
    faq_collection = get_collection("faq")
    faq_doc = {
        "question": payload.question.strip(),
        "answer": payload.answer.strip()
    }
    
    result = await faq_collection.insert_one(faq_doc)
    faq_doc["_id"] = result.inserted_id
    
    logger.info(f"Admin {current_admin['email']} created FAQ: '{payload.question}'")
    return faq_doc

@router.get("", response_model=List[FAQResponse])
async def list_faqs(current_user: dict = Depends(get_current_user)):
    """Retrieve list of all FAQs."""
    faq_collection = get_collection("faq")
    cursor = faq_collection.find()
    
    faqs = []
    async for faq in cursor:
        faqs.append(faq)
        
    return faqs

@router.delete("/{faq_id}", status_code=status.HTTP_200_OK)
async def delete_faq(
    faq_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Delete an FAQ entry. Only accessible by administrators."""
    if not ObjectId.is_valid(faq_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid FAQ ID"
        )
        
    obj_id = ObjectId(faq_id)
    faq_collection = get_collection("faq")
    
    faq = await faq_collection.find_one({"_id": obj_id})
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
        
    await faq_collection.delete_one({"_id": obj_id})
    logger.info(f"Admin {current_admin['email']} deleted FAQ: '{faq['question']}'")
    
    return {"message": "FAQ deleted successfully"}
