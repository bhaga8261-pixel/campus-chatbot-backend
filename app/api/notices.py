import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.jwt_handler import get_current_admin, get_current_user
from app.database.connection import get_collection
from app.models.models import NoticeCreate, NoticeResponse
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notices", tags=["Notices"])

@router.post("", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
async def create_notice(
    payload: NoticeCreate,
    current_admin: dict = Depends(get_current_admin)
):
    """Create a college notice. Only accessible by administrators."""
    notices_collection = get_collection("notices")
    notice_doc = {
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "createdAt": datetime.utcnow()
    }
    
    result = await notices_collection.insert_one(notice_doc)
    notice_doc["_id"] = result.inserted_id
    
    logger.info(f"Admin {current_admin['email']} created notice: '{payload.title}'")
    return notice_doc

@router.get("", response_model=List[NoticeResponse])
async def list_notices(current_user: dict = Depends(get_current_user)):
    """Retrieve list of all notices sorted by release date (newest first)."""
    notices_collection = get_collection("notices")
    cursor = notices_collection.find().sort("createdAt", -1)
    
    notices = []
    async for notice in cursor:
        notices.append(notice)
        
    return notices

@router.delete("/{notice_id}", status_code=status.HTTP_200_OK)
async def delete_notice(
    notice_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Delete a notice. Only accessible by administrators."""
    if not ObjectId.is_valid(notice_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notice ID"
        )
        
    obj_id = ObjectId(notice_id)
    notices_collection = get_collection("notices")
    
    notice = await notices_collection.find_one({"_id": obj_id})
    if not notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notice not found"
        )
        
    await notices_collection.delete_one({"_id": obj_id})
    logger.info(f"Admin {current_admin['email']} deleted notice: '{notice['title']}'")
    
    return {"message": "Notice deleted successfully"}
