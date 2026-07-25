"""Chat request/response contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_CHARS = 4000


class MessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    conversation_id: str | None = Field(default=None, max_length=64)
    history: list[MessageIn] | None = Field(
        default=None,
        max_length=40,
        description="Optional client-side history. Server history wins when a "
        "conversation_id is supplied.",
    )

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message cannot be blank")
        return v


class ToolCallOut(BaseModel):
    name: str
    arguments: dict = {}
    ok: bool = True
    duration_ms: int = 0


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    message_id: int
    tools_used: list[str] = []
    tool_calls: list[ToolCallOut] = []
    model: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class ConversationOut(BaseModel):
    id: str
    title: str
    message_count: int = 0
    created_at: str
    updated_at: str


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []
