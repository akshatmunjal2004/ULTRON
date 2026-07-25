"""Shared FastAPI dependencies.

Endpoints declare what they need here rather than importing singletons, which
is what makes them straightforward to test with overrides.
"""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import Depends, Query

from app.db.session import get_db
from app.services.agent_service import AgentService, get_agent_service
from app.tools.registry import ToolRegistry, get_registry

DbConn = Annotated[sqlite3.Connection, Depends(get_db)]
Agent = Annotated[AgentService, Depends(get_agent_service)]
Tools = Annotated[ToolRegistry, Depends(get_registry)]


class Pagination:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PageParams = Annotated[Pagination, Depends(Pagination)]
