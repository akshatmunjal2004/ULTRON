"""The single place tools are registered.

Adding a tool is one import plus one list entry. Schemas, validation, the
/tools endpoint and the agent's tool list all read from here, so there is
nothing to keep in sync by hand.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.logging import get_logger
from app.tools.base import BaseTool, ToolResult
from app.tools.code_runner import CodeRunnerTool
from app.tools.file_ops import FileOpsTool
from app.tools.memory_tool import MemoryTool
from app.tools.open_url import OpenUrlTool
from app.tools.system_info import SystemInfoTool
from app.tools.web_search import WebSearchTool

logger = get_logger(__name__)

_TOOL_CLASSES: tuple[type[BaseTool], ...] = (
    WebSearchTool,
    MemoryTool,
    SystemInfoTool,
    FileOpsTool,
    OpenUrlTool,
    CodeRunnerTool,
)


class ToolRegistry:
    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools: dict[str, BaseTool] = {t.name: t for t in tools}

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def enabled(self) -> list[BaseTool]:
        return [t for t in self._tools.values() if t.enabled]

    def enabled_names(self) -> list[str]:
        return [t.name for t in self.enabled()]

    def schemas(self) -> list[dict[str, Any]]:
        """Function schemas for the LLM. Disabled tools are not advertised, so
        the model never proposes a call that is guaranteed to fail."""
        return [t.json_schema() for t in self.enabled()]

    def execute(self, name: str, args: dict[str, Any] | None) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                tool=name, result=f"There is no tool called '{name}'.", ok=False
            )
        result = tool.run(args)
        logger.info(
            "tool=%s ok=%s duration_ms=%s", result.tool, result.ok, result.duration_ms
        )
        return result


@lru_cache(maxsize=1)
def get_registry() -> ToolRegistry:
    return ToolRegistry([cls() for cls in _TOOL_CLASSES])
