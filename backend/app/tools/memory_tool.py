"""Let the agent read and write the long-term memory table."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.db.repositories import memory_repo
from app.db.session import get_conn
from app.tools.base import BaseTool


class MemoryParams(BaseModel):
    action: Literal["save", "recall", "list", "forget"] = Field(
        description="save stores a fact, recall looks one up, list returns all, "
        "forget deletes one."
    )
    key: str = Field(default="", max_length=120)
    value: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _check_required(self) -> MemoryParams:
        if self.action == "save" and (not self.key.strip() or not self.value.strip()):
            raise ValueError("save needs both key and value")
        if self.action in {"recall", "forget"} and not self.key.strip():
            raise ValueError(f"{self.action} needs a key")
        return self


class MemoryTool(BaseTool):
    name = "memory_tool"
    description = (
        "Remember facts about the user across conversations, or recall what you "
        "already know. Use it whenever the user says to remember something."
    )
    params_model = MemoryParams

    def execute(self, params: MemoryParams) -> str:
        with get_conn() as conn:
            if params.action == "save":
                item = memory_repo.upsert(conn, params.key, params.value)
                return f"Saved. {item['key']}: {item['value']}"

            if params.action == "recall":
                exact = memory_repo.get_by_key(conn, params.key)
                if exact:
                    return f"{exact['key']}: {exact['value']}"
                matches = memory_repo.search(conn, params.key, limit=5)
                if matches:
                    lines = "\n".join(f"- {m['key']}: {m['value']}" for m in matches)
                    return f"Nothing exact, but these are close:\n{lines}"
                return f"Nothing stored under '{params.key}'."

            if params.action == "forget":
                removed = memory_repo.delete(conn, params.key)
                return (
                    f"Forgot '{params.key}'."
                    if removed
                    else f"Nothing stored under '{params.key}'."
                )

            items, total = memory_repo.list_all(conn, limit=50)
            if not items:
                return "Memory is empty."
            lines = "\n".join(f"- {i['key']}: {i['value']}" for i in items)
            return f"{total} fact(s) stored:\n{lines}"
