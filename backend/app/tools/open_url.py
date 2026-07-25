"""Hand a URL to the user's browser.

The original version called webbrowser.open() on the machine running the API.
Over a network that opens tabs on the *server*, which is both useless to the
user and a nice denial-of-service primitive. This version validates the URL and
returns it; the frontend is what actually opens it.
"""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.tools.base import BaseTool

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"}


class OpenUrlParams(BaseModel):
    url: str = Field(min_length=4, max_length=2000, description="The URL to open.")

    @field_validator("url")
    @classmethod
    def _normalise(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("only http and https URLs are allowed")
        host = (parsed.hostname or "").lower()
        if not host:
            raise ValueError("the URL has no host")
        if host in BLOCKED_HOSTS or host.endswith(".local"):
            raise ValueError("internal addresses are not allowed")
        return v


class OpenUrlTool(BaseTool):
    name = "open_url"
    description = (
        "Open a website in the user's browser. Returns the link that the app "
        "will open on the user's machine."
    )
    params_model = OpenUrlParams

    def execute(self, params: OpenUrlParams) -> str:
        return f"OPEN_URL::{params.url}"
