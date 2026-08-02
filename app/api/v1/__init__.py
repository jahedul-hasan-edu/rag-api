"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import search, upload

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(upload.router)
api_router.include_router(search.router)
