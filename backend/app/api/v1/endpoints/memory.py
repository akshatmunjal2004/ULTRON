"""CRUD over the long-term memory table."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbConn, PageParams
from app.core.errors import NotFoundError
from app.core.security import require_api_key
from app.db.repositories import memory_repo
from app.schemas.common import Deleted, Page
from app.schemas.memory import MemoryCreate, MemoryOut

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=Page[MemoryOut], summary="List stored facts")
def list_memory(
    conn: DbConn,
    page: PageParams,
    q: str | None = Query(default=None, max_length=120, description="Filter by text"),
) -> Page[MemoryOut]:
    if q:
        items = memory_repo.search(conn, q, limit=page.limit)
        return Page[MemoryOut](
            items=[MemoryOut(**i) for i in items],
            total=len(items),
            limit=page.limit,
            offset=0,
        )
    items, total = memory_repo.list_all(conn, limit=page.limit, offset=page.offset)
    return Page[MemoryOut](
        items=[MemoryOut(**i) for i in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{key}", response_model=MemoryOut, summary="Read one fact")
def get_memory(key: str, conn: DbConn) -> MemoryOut:
    item = memory_repo.get_by_key(conn, key)
    if not item:
        raise NotFoundError(f"Nothing is stored under '{key}'.")
    return MemoryOut(**item)


@router.put(
    "",
    response_model=MemoryOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_api_key)],
    summary="Create or update a fact",
)
def upsert_memory(payload: MemoryCreate, conn: DbConn) -> MemoryOut:
    # PUT rather than POST: the key is the identifier and the write is idempotent.
    return MemoryOut(**memory_repo.upsert(conn, payload.key, payload.value))


@router.delete(
    "/{key}",
    response_model=Deleted,
    dependencies=[Depends(require_api_key)],
    summary="Delete a fact",
)
def delete_memory(key: str, conn: DbConn) -> Deleted:
    if not memory_repo.delete(conn, key):
        raise NotFoundError(f"Nothing is stored under '{key}'.")
    return Deleted(deleted=True, id=key)
