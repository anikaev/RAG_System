from fastapi import APIRouter

from app.api.routes_chat import router as chat_router
from app.api.routes_code import router as code_router
from app.api.routes_health import router as health_router
from app.api.routes_kb import router as kb_router
from app.api.routes_playground import router as playground_router
from app.api.routes_retrieval import router as retrieval_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(code_router)
api_router.include_router(kb_router)
api_router.include_router(retrieval_router)
api_router.include_router(playground_router)
