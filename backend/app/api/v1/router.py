"""Aggregates every v1 endpoint module into one router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import chat, health, memory, tools, voice

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(memory.router)
api_router.include_router(tools.router)
api_router.include_router(voice.router)
