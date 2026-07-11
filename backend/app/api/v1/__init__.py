"""API v1 router — aggregates all endpoint routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, events, exchange_rates, health, users, wallets

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(wallets.router)
api_router.include_router(exchange_rates.router)
api_router.include_router(events.router)
