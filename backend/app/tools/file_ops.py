"""Read, write, list and delete files inside the workspace directory.

Path containment is enforced with Path.resolve() plus is_relative_to(). The
previous implementation compared with str.startswith(), which lets a sibling
directory named `workspace-notes` pass a check against `workspace`, and which
follows symlinks straight out of the sandbox.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.config import settings
from app.tools.base import BaseTool

MAX_READ_CHARS = 20_000
MAX_WRITE_CHARS = 100_000


class FileOpsParams(BaseModel):
    action: Literal["read", "write", "append", "list", "delete"]
    filename: str = Field(default="", max_length=255)
    content: str = Field(default="", max_length=MAX_WRITE_CHARS)

    @model_validator(mode="after")
    def _check_required(self) -> FileOpsParams:
        if self.action != "list" and not self.filename.strip():
            raise ValueError(f"{self.action} needs a filename")
        if self.action in {"write", "append"} and not self.content:
            raise ValueError(f"{self.action} needs content")
        return self


def resolve_in_workspace(filename: str) -> Path:
    """Resolve `filename` inside the workspace or raise."""
    root = Path(settings.WORKSPACE_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)

    candidate = Path(filename)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Only paths inside the workspace are allowed.")

    target = (root / candidate).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Only paths inside the workspace are allowed.")
    return target


class FileOpsTool(BaseTool):
    name = "file_ops"
    description = (
        "Read, write, append to, list or delete text files in the agent workspace "
        "folder. Paths are confined to that folder."
    )
    params_model = FileOpsParams

    @property
    def enabled(self) -> bool:
        return settings.ENABLE_FILE_OPS

    def execute(self, params: FileOpsParams) -> str:
        root = Path(settings.WORKSPACE_DIR)

        if params.action == "list":
            root.mkdir(parents=True, exist_ok=True)
            names = sorted(p.name for p in root.iterdir() if p.is_file())
            return "Files: " + (", ".join(names) if names else "(empty)")

        target = resolve_in_workspace(params.filename)

        if params.action == "read":
            if not target.is_file():
                return f"'{params.filename}' does not exist in the workspace."
            text = target.read_text(encoding="utf-8", errors="replace")
            if len(text) > MAX_READ_CHARS:
                return text[:MAX_READ_CHARS] + "\n... (truncated)"
            return text or "(the file is empty)"

        if params.action in {"write", "append"}:
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if params.action == "append" else "w"
            with target.open(mode, encoding="utf-8") as handle:
                handle.write(params.content)
            verb = "Appended" if params.action == "append" else "Wrote"
            return f"{verb} {len(params.content)} characters to '{params.filename}'."

        if not target.is_file():
            return f"'{params.filename}' does not exist in the workspace."
        target.unlink()
        return f"Deleted '{params.filename}'."
