import sys
sys.path.append("../")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from trading_rules_backend.config import settings
from trading_rules_backend.app.router import api_router


def create_app() -> FastAPI:

    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
