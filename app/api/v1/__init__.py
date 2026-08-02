"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import chat, search, upload

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(upload.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)
