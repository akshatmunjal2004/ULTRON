"""The agent loop.

Responsibilities kept deliberately narrow: build the message list, run the
tool-calling loop, and hand back a reply plus an audit trail. Persistence lives
in the endpoint, tool execution lives in the registry, and the HTTP call lives
in groq_client.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.prompts.system import AGENT_SYSTEM_PROMPT
from app.services import groq_client
from app.tools.registry import ToolRegistry, get_registry

logger = get_logger(__name__)


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    result: str
    ok: bool
    duration_ms: int


@dataclass
class AgentResult:
    reply: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    model: str = ""

    @property
    def tools_used(self) -> list[str]:
        seen: list[str] = []
        for call in self.tool_calls:
            if call.name not in seen:
                seen.append(call.name)
        return seen


class AgentService:
    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or get_registry()

    # -- message assembly --------------------------------------------------
    def _build_messages(
        self, message: str, history: list[dict[str, str]] | None
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT}
        ]
        for turn in (history or [])[-settings.AGENT_HISTORY_TURNS :]:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})
        return messages

    @staticmethod
    def _parse_args(raw: str | None) -> dict[str, Any]:
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError:
            logger.warning("Model produced unparseable tool arguments: %r", raw)
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _run_tool_calls(
        self, tool_calls: Any, messages: list[dict[str, Any]]
    ) -> list[ToolCallRecord]:
        """Execute every call the model asked for and append the results."""
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        records: list[ToolCallRecord] = []
        for call in tool_calls:
            name = call.function.name
            args = self._parse_args(call.function.arguments)
            result = self.registry.execute(name, args)
            records.append(
                ToolCallRecord(
                    name=name,
                    arguments=args,
                    result=result.result,
                    ok=result.ok,
                    duration_ms=result.duration_ms,
                )
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": result.result[: settings.AGENT_TOOL_RESULT_CHAR_LIMIT],
                }
            )
        return records

    # -- public API --------------------------------------------------------
    def run(self, message: str, history: list[dict[str, str]] | None = None) -> AgentResult:
        messages = self._build_messages(message, history)
        schemas = self.registry.schemas()
        calls: list[ToolCallRecord] = []

        completion = groq_client.chat_completion(messages, tools=schemas)
        choice = completion.choices[0].message

        steps = 0
        while getattr(choice, "tool_calls", None) and steps < settings.AGENT_MAX_TOOL_STEPS:
            calls.extend(self._run_tool_calls(choice.tool_calls, messages))
            completion = groq_client.chat_completion(messages, tools=schemas)
            choice = completion.choices[0].message
            steps += 1

        if steps >= settings.AGENT_MAX_TOOL_STEPS and getattr(choice, "tool_calls", None):
            logger.warning("Tool budget of %s steps exhausted", settings.AGENT_MAX_TOOL_STEPS)

        reply = (choice.content or "").strip() or (
            "I could not put an answer together for that one. Try rephrasing it."
        )
        return AgentResult(reply=reply, tool_calls=calls, model=settings.LLM_MODEL)

    def stream(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> Iterator[dict[str, Any]]:
        """Yield events for Server-Sent Events.

        Tools resolve first (they are not streamable), then the final answer is
        streamed token by token so speech can start before generation finishes.
        """
        messages = self._build_messages(message, history)
        schemas = self.registry.schemas()
        calls: list[ToolCallRecord] = []

        yield {"event": "status", "data": {"state": "thinking"}}

        completion = groq_client.chat_completion(messages, tools=schemas)
        choice = completion.choices[0].message

        steps = 0
        while getattr(choice, "tool_calls", None) and steps < settings.AGENT_MAX_TOOL_STEPS:
            for call in choice.tool_calls:
                yield {"event": "tool", "data": {"name": call.function.name}}
            calls.extend(self._run_tool_calls(choice.tool_calls, messages))
            completion = groq_client.chat_completion(messages, tools=schemas)
            choice = completion.choices[0].message
            steps += 1

        if getattr(choice, "tool_calls", None):
            # Budget spent. Ask once more without tools so we always answer.
            messages.append(
                {
                    "role": "user",
                    "content": "Answer now with what you have. Do not call more tools.",
                }
            )

        yield {"event": "status", "data": {"state": "answering"}}

        pieces: list[str] = []
        stream = groq_client.chat_completion(messages, stream=True)
        for chunk in stream:
            delta = chunk.choices[0].delta
            token = getattr(delta, "content", None)
            if token:
                pieces.append(token)
                yield {"event": "token", "data": {"text": token}}

        reply = "".join(pieces).strip() or "I could not put an answer together."
        yield {
            "event": "done",
            "data": {
                "reply": reply,
                "tools_used": [c.name for c in calls],
                "model": settings.LLM_MODEL,
            },
        }


_service: AgentService | None = None


def get_agent_service() -> AgentService:
    """Dependency provider. One instance, created lazily so that importing this
    module never requires an API key."""
    global _service
    if _service is None:
        _service = AgentService()
    return _service
