"""Memory CRUD contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MemoryCreate(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=2000)

    @field_validator("key", "value")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("cannot be blank")
        return v


class MemoryOut(BaseModel):
    id: int
    key: str
    value: str
    created_at: str
    updated_at: str
