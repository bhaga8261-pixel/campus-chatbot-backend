import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.jwt_handler import get_current_admin, get_current_user
from app.database.connection import get_collection
from app.models.models import EventCreate, EventResponse
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])

@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    current_admin: dict = Depends(get_current_admin)
):
    """Create a college event. Only accessible by administrators."""
    events_collection = get_collection("events")
    event_doc = {
        "title": payload.title.strip(),
        "date": payload.date,
        "description": payload.description.strip()
    }
    
    result = await events_collection.insert_one(event_doc)
    event_doc["_id"] = result.inserted_id
    
    logger.info(f"Admin {current_admin['email']} created event: '{payload.title}'")
    return event_doc

@router.get("", response_model=List[EventResponse])
async def list_events(current_user: dict = Depends(get_current_user)):
    """Retrieve list of all upcoming/scheduled events."""
    events_collection = get_collection("events")
    # Sort events by date ascending (soonest event first)
    cursor = events_collection.find().sort("date", 1)
    
    events = []
    async for event in cursor:
        events.append(event)
        
    return events

@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
async def delete_event(
    event_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Delete an event. Only accessible by administrators."""
    if not ObjectId.is_valid(event_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID"
        )
        
    obj_id = ObjectId(event_id)
    events_collection = get_collection("events")
    
    event = await events_collection.find_one({"_id": obj_id})
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
        
    await events_collection.delete_one({"_id": obj_id})
    logger.info(f"Admin {current_admin['email']} deleted event: '{event['title']}'")
    
    return {"message": "Event deleted successfully"}
