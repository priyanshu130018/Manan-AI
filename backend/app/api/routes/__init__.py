from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.profile import router as profile_router
from app.api.routes.chat import router as chat_router
from app.api.routes.sessions import router as session_router
from app.api.routes.documents import router as document_router
from app.api.routes.memory import router as memory_router
from app.api.routes.messages import router as messages_router
from app.api.routes.models import router as models_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(profile_router)
api_router.include_router(chat_router)
api_router.include_router(session_router)
api_router.include_router(document_router)
api_router.include_router(memory_router)
api_router.include_router(messages_router)
api_router.include_router(models_router)

