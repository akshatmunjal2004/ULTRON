"""Tool contract.

The old code kept two parallel definitions of every tool: a hand-written JSON
schema for the model, and a Python function with its own signature. They drifted
apart silently. Here each tool declares one Pydantic `Params` model, and both the
schema the LLM sees and the validation the executor applies are derived from it,
so they cannot disagree.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)


class ToolResult(BaseModel):
    tool: str
    result: str
    ok: bool = True
    duration_ms: int = 0


class NoParams(BaseModel):
    """Marker for tools that take no arguments."""


class BaseTool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    params_model: ClassVar[type[BaseModel]] = NoParams
    requires_auth: ClassVar[bool] = False
    # Hard ceiling on what a single tool may hand back to the model.
    max_result_chars: ClassVar[int] = 8000

    @property
    def enabled(self) -> bool:
        """Feature-flag hook. Disabled tools are hidden from the model."""
        return True

    @property
    def disabled_reason(self) -> str:
        return f"The '{self.name}' tool is switched off on this server."

    @abstractmethod
    def execute(self, params: Any) -> str:
        """Run the tool. Receives a validated params_model instance."""

    # -- schema ------------------------------------------------------------
    def json_schema(self) -> dict[str, Any]:
        """OpenAI/Groq-compatible function schema, generated from params_model."""
        schema = self.params_model.model_json_schema()
        schema.pop("title", None)
        schema.pop("$defs", None)
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }

    # -- execution ---------------------------------------------------------
    def run(self, raw_args: dict[str, Any] | None) -> ToolResult:
        """Validate arguments, execute, and never raise."""
        started = time.perf_counter()

        def finish(text: str, ok: bool) -> ToolResult:
            elapsed = int((time.perf_counter() - started) * 1000)
            return ToolResult(
                tool=self.name,
                result=text[: self.max_result_chars],
                ok=ok,
                duration_ms=elapsed,
            )

        if not self.enabled:
            return finish(self.disabled_reason, False)

        try:
            params = self.params_model.model_validate(raw_args or {})
        except ValidationError as exc:
            issues = "; ".join(
                f"{'.'.join(str(p) for p in e['loc']) or 'input'}: {e['msg']}"
                for e in exc.errors()
            )
            return finish(f"Invalid arguments for '{self.name}': {issues}", False)

        try:
            return finish(str(self.execute(params)), True)
        except Exception as exc:  # noqa: BLE001 - tools must never crash the agent
            logger.warning("Tool %s failed: %s", self.name, exc, exc_info=True)
            return finish(f"The '{self.name}' tool failed: {exc}", False)
