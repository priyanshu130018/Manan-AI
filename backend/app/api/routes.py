from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.api.document import router as document_router

class RouteRegistry:
    def __init__(self) -> None:
        self.router = APIRouter()

    def register_routes(self) -> APIRouter:
        self.router.include_router(health_router)
        self.router.include_router(chat_router)
        self.router.include_router(upload_router)
        self.router.include_router(document_router)

        return self.router


route_registry = RouteRegistry()