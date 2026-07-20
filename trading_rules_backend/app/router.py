from fastapi import APIRouter
from trading_rules_backend.app.routes import rules

api_router = APIRouter()
api_router.include_router(rules.router)