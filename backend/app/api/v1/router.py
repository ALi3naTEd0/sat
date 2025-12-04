"""
API V1 Router - Main router combining all endpoints
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, fiscal, credentials, cfdi, cfdis, declaraciones, sync

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(fiscal.router)
api_router.include_router(credentials.router)
api_router.include_router(cfdi.router)
api_router.include_router(cfdis.router)
api_router.include_router(declaraciones.router)
api_router.include_router(sync.router)
