"""DuckDuckGo web search."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.config import settings
from app.tools.base import BaseTool


class WebSearchParams(BaseModel):
    query: str = Field(min_length=2, max_length=300, description="The search query.")
    max_results: int = Field(default=5, ge=1, le=10, description="How many results.")


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for current information, news or facts you do not know. "
        "Use this whenever the answer depends on something recent."
    )
    params_model = WebSearchParams

    @property
    def enabled(self) -> bool:
        return settings.ENABLE_WEB_SEARCH

    def execute(self, params: WebSearchParams) -> str:
        try:
            from ddgs import DDGS
        except ImportError:  # pragma: no cover - older package name
            from duckduckgo_search import DDGS  # type: ignore[no-redef]

        lines: list[str] = []
        with DDGS() as ddgs:
            for item in ddgs.text(params.query, max_results=params.max_results):
                title = (item.get("title") or "").strip()
                body = (item.get("body") or "").strip()
                href = (item.get("href") or "").strip()
                lines.append(f"- {title}: {body} ({href})")

        if not lines:
            return f"No results found for '{params.query}'."
        return f"Web results for '{params.query}':\n" + "\n".join(lines)
