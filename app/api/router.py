from fastapi import APIRouter
from app.api import auth, chat, documents, notices, events, faq, admin

api_router = APIRouter()

# Include all the API endpoints
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(documents.router)
api_router.include_router(notices.router)
api_router.include_router(events.router)
api_router.include_router(faq.router)
api_router.include_router(admin.router) # contains /embeddings/rebuild, /system/status, /system/users
