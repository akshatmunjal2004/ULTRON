"""Chat endpoints: request/response, streaming, and conversation history."""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import Agent, DbConn, PageParams
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.core.security import require_api_key
from app.db.repositories import conversation_repo
from app.db.session import get_conn
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationOut,
    MessageOut,
    ToolCallOut,
)
from app.schemas.common import Deleted, Page

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])


def _history_for(conn, payload: ChatRequest) -> tuple[str, list[dict[str, str]]]:
    """Resolve the conversation and the turns to replay to the model.

    Server-side history wins over anything the client sends, so a tampered or
    stale client cannot rewrite what the agent thinks was said.
    """
    conversation_id = conversation_repo.ensure(
        conn, payload.conversation_id, seed_title=payload.message
    )
    history = conversation_repo.recent_messages(
        conn, conversation_id, settings.AGENT_HISTORY_TURNS
    )
    if not history and payload.history:
        history = [{"role": m.role, "content": m.content} for m in payload.history]
    return conversation_id, history


@router.post("/chat", response_model=ChatResponse, summary="Send a message")
def chat(payload: ChatRequest, conn: DbConn, agent: Agent) -> ChatResponse:
    conversation_id, history = _history_for(conn, payload)
    conversation_repo.add_message(conn, conversation_id, "user", payload.message)

    result = agent.run(payload.message, history)

    message_id = conversation_repo.add_message(
        conn, conversation_id, "assistant", result.reply
    )
    conversation_repo.add_tool_calls(
        conn,
        message_id,
        [
            {
                "name": c.name,
                "arguments": c.arguments,
                "result": c.result,
                "ok": c.ok,
                "duration_ms": c.duration_ms,
            }
            for c in result.tool_calls
        ],
    )

    return ChatResponse(
        reply=result.reply,
        conversation_id=conversation_id,
        message_id=message_id,
        tools_used=result.tools_used,
        tool_calls=[
            ToolCallOut(
                name=c.name, arguments=c.arguments, ok=c.ok, duration_ms=c.duration_ms
            )
            for c in result.tool_calls
        ],
        model=result.model,
    )


@router.post("/chat/stream", summary="Send a message and stream the reply")
def chat_stream(payload: ChatRequest, agent: Agent) -> StreamingResponse:
    """Server-Sent Events. Each frame is `event: <name>` plus a JSON `data:` line.

    This opens its own short DB transactions rather than using the request-scoped
    connection, because the generator runs after the dependency has been closed.
    """

    with get_conn() as conn:
        conversation_id, history = _history_for(conn, payload)
        conversation_repo.add_message(conn, conversation_id, "user", payload.message)

    def frames() -> Iterator[str]:
        yield f"event: start\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"
        reply = ""
        tools_used: list[str] = []
        try:
            for item in agent.stream(payload.message, history):
                if item["event"] == "done":
                    reply = item["data"]["reply"]
                    tools_used = item["data"]["tools_used"]
                yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"
        except Exception as exc:  # noqa: BLE001 - the stream must close cleanly
            logger.exception("Streaming chat failed")
            payload_err = {"code": "stream_failed", "message": str(exc)}
            yield f"event: error\ndata: {json.dumps(payload_err)}\n\n"
        finally:
            if reply:
                with get_conn() as conn:
                    message_id = conversation_repo.add_message(
                        conn, conversation_id, "assistant", reply
                    )
                    conversation_repo.add_tool_calls(
                        conn,
                        message_id,
                        [{"name": name} for name in tools_used],
                    )

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/conversations", response_model=Page[ConversationOut], summary="List conversations"
)
def list_conversations(conn: DbConn, page: PageParams) -> Page[ConversationOut]:
    items, total = conversation_repo.list_conversations(
        conn, limit=page.limit, offset=page.offset
    )
    return Page[ConversationOut](
        items=[ConversationOut(**i) for i in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Read one conversation",
)
def get_conversation(conversation_id: str, conn: DbConn) -> ConversationDetail:
    items, _ = conversation_repo.list_conversations(conn, limit=1000)
    match = next((c for c in items if c["id"] == conversation_id), None)
    if match is None:
        raise NotFoundError("That conversation does not exist.")
    messages = conversation_repo.list_messages(conn, conversation_id)
    return ConversationDetail(
        **match, messages=[MessageOut(**m) for m in messages]
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=Deleted,
    dependencies=[Depends(require_api_key)],
    summary="Delete a conversation",
)
def delete_conversation(conversation_id: str, conn: DbConn) -> Deleted:
    if not conversation_repo.delete(conn, conversation_id):
        raise NotFoundError("That conversation does not exist.")
    return Deleted(deleted=True, id=conversation_id)
