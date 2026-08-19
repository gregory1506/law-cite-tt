from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import AsyncOpenAI

from api.tools import HANDLERS, TOOL_DEFINITIONS
from scraper.db_pg import LawCitePGDB

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MAX_ITERATIONS = 8
MAX_TOOL_TEXT = 6000

SYSTEM_PROMPT = (
    "You are a grounded legal research assistant for the Laws of Trinidad and "
    "Tobago. You answer questions about statutory provisions by calling the "
    "provided tools, which query the official source corpus. "
    "Rules: never invent a statute, chapter, section, date, or quotation — every "
    "factual claim must come from a tool result. If the tools return nothing "
    "relevant, say so plainly. Cite only sources returned by the tools. "
    "Stop after one or two tool calls once you have enough to answer concisely — "
    "do not search exhaustively. "
    "For any question about statutes, reply with a single JSON object of the form "
    '{"answer": "your answer to the user", "source_ids": ["ids of the tool '
    'sources your answer relies on"]}. Include every source you rely on in '
    'source_ids; use exactly the ids given in tool results. '
    "For non-legal or conversational questions, answer in plain text without "
    "calling tools and without JSON."
)


class AgentConfig:
    def __init__(self) -> None:
        self.api_key: str = os.environ.get("OPENAI_API_KEY", "")
        self.base_url: str = os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL
        self.model: str = os.environ.get("LAWCITE_AGENT_MODEL") or DEFAULT_MODEL

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def _parse_structured_reply(content: str) -> dict[str, Any] | None:
    """Extract the model's JSON reply, tolerating prose around it."""
    if not content:
        return None
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "answer" not in data:
        return None
    source_ids = data.get("source_ids")
    if not isinstance(source_ids, list):
        source_ids = []
    return {"answer": str(data["answer"]), "source_ids": [str(s) for s in source_ids]}


def _unknown_source_ids(reply: dict[str, Any], allowed: set[str]) -> list[str]:
    return [sid for sid in reply["source_ids"] if sid not in allowed]


def _grounded(reply: dict[str, Any], allowed: set[str]) -> bool:
    return bool(reply["source_ids"]) and not _unknown_source_ids(reply, allowed)


class ChatAgent:
    def __init__(self, db: LawCitePGDB, config: AgentConfig | None = None):
        self.db = db
        self.config = config or AgentConfig()

    async def run(
        self,
        messages: list[dict[str, str]],
        *,
        mode: str = "research",
    ) -> dict[str, Any]:
        if not self.config.configured:
            return {
                "status": "unconfigured",
                "answer": (
                    "The research assistant is not configured. Set OPENAI_API_KEY "
                    "to enable it."
                ),
                "sources": [],
            }

        client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )
        tools = TOOL_DEFINITIONS
        history: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ]
        collected_sources: list[dict[str, Any]] = []
        allowed_ids: set[str] = set()

        for _ in range(MAX_ITERATIONS):
            try:
                response = await client.chat.completions.create(
                    model=self.config.model,
                    messages=history,
                    tools=tools,
                    temperature=0.1,
                )
            except Exception as error:
                logger.warning("chat completion failed: %s", error)
                return {
                    "status": "error",
                    "answer": (
                        "The research assistant hit an error contacting the model. "
                        "Try again shortly."
                    ),
                    "sources": collected_sources,
                }

            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                reply = _parse_structured_reply(message.content or "")
                if not allowed_ids:
                    return {
                        "status": "ok",
                        "answer": (
                            (reply or {}).get("answer", message.content)
                            or "No answer was produced."
                        ),
                        "sources": [],
                    }
                if reply is None:
                    logger.warning(
                        "refused: non-JSON reply after tools; content=%r",
                        (message.content or "")[:400],
                    )
                    return {
                        "status": "refused",
                        "answer": (
                            "I could not verify that answer against the Laws "
                            "of Trinidad and Tobago, so I will not state it as "
                            "fact. Use Research or Cite to check the source "
                            "directly."
                        ),
                        "sources": collected_sources,
                    }
                if _grounded(reply, allowed_ids):
                    return {
                        "status": "ok",
                        "answer": reply["answer"],
                        "sources": collected_sources,
                    }
                logger.warning(
                    "refused: ungrounded reply; source_ids=%r allowed=%s content=%r",
                    reply["source_ids"],
                    sorted(allowed_ids)[:5],
                    (message.content or "")[:400],
                )
                return {
                    "status": "refused",
                    "answer": (
                        "I could not verify that answer against the Laws of "
                        "Trinidad and Tobago, so I will not state it as fact. "
                        "Use Research or Cite to check the source directly."
                    ),
                    "sources": collected_sources,
                }

            history.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                            **(
                                {"extra_content": tc.model_extra["extra_content"]}
                                if (getattr(tc, "model_extra", None) or {}).get(
                                    "extra_content"
                                )
                                else {}
                            ),
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tool_call in tool_calls:
                handler = HANDLERS.get(tool_call.function.name)
                if handler is None:
                    tool_text = "Unknown tool."
                else:
                    try:
                        arguments = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        arguments = {}
                    try:
                        result = await handler(self.db, **arguments)
                        tool_text = result["text"][:MAX_TOOL_TEXT]
                        for source in result["sources"]:
                            collected_sources.append(source)
                            allowed_ids.add(source["id"])
                    except Exception as error:
                        logger.warning("tool %s failed: %s", tool_call.function.name, error)
                        tool_text = "Tool call failed; report that the lookup could not be completed."
                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_text,
                    }
                )

        return {
            "status": "error",
            "answer": (
                "The research assistant exceeded its step budget without reaching "
                "an answer. Try a more specific question."
            ),
            "sources": collected_sources,
        }