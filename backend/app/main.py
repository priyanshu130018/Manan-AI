from fastapi import FastAPI

from app.api.routes import route_registry
from app.core.config import get_settings
from app.middleware.cors import setup_cors

settings = get_settings()


class Application:
    def __init__(self) -> None:
        self.app = FastAPI(
            title=settings.app_name,
            version="1.0.0",
        )

        setup_cors(self.app)

        self._register_routes()

    def _register_routes(self) -> None:
        self.app.include_router(
            route_registry.register_routes(),
        )

    def get_app(self) -> FastAPI:
        return self.app


application = Application()

app = application.get_app()