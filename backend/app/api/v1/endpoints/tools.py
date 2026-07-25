"""Tool discovery and direct invocation.

Direct invocation exists for debugging and for UI buttons. It is behind the API
key because it reaches the same executors the agent uses, including the one that
runs Python.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import Tools
from app.core.errors import NotFoundError
from app.core.security import require_api_key
from app.schemas.tools import (
    ToolExecuteRequest,
    ToolExecuteResponse,
    ToolInfo,
    ToolListResponse,
)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse, summary="List available tools")
def list_tools(tools: Tools) -> ToolListResponse:
    return ToolListResponse(
        tools=[
            ToolInfo(
                name=tool.name,
                description=tool.description,
                enabled=tool.enabled,
                requires_auth=tool.requires_auth,
                parameters=tool.json_schema()["function"]["parameters"],
            )
            for tool in tools.all()
        ]
    )


@router.post(
    "/execute",
    response_model=ToolExecuteResponse,
    dependencies=[Depends(require_api_key)],
    summary="Run a tool directly",
)
def execute_tool(payload: ToolExecuteRequest, tools: Tools) -> ToolExecuteResponse:
    if tools.get(payload.tool) is None:
        raise NotFoundError(f"There is no tool called '{payload.tool}'.")
    result = tools.execute(payload.tool, payload.args)
    return ToolExecuteResponse(
        tool=result.tool,
        result=result.result,
        ok=result.ok,
        duration_ms=result.duration_ms,
    )
