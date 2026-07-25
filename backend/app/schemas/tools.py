"""Tool discovery and manual-execution contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    name: str
    description: str
    enabled: bool
    requires_auth: bool
    parameters: dict


class ToolListResponse(BaseModel):
    tools: list[ToolInfo]


class ToolExecuteRequest(BaseModel):
    tool: str = Field(min_length=1, max_length=64)
    args: dict = {}


class ToolExecuteResponse(BaseModel):
    tool: str
    result: str
    ok: bool
    duration_ms: int
